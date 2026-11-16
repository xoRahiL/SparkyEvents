"""Unit and integration tests for Phase 1 security hardening."""
import io
from unittest.mock import patch
from PIL import Image

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse

from appspark.forms import WorkhandProfileForm, CompanyProfileForm, MAX_UPLOAD_SIZE
from appspark.models import Workhand, WorkhandCategory, Company, Event, EventsCategory
from appspark.views import generate_otp, MAX_OTP_ATTEMPTS


class SecurityOtpRegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = WorkhandCategory.objects.create(category="Decoration")
        self.event_category = EventsCategory.objects.create(category="Wedding")

    def test_generate_otp_format(self):
        """OTP must be a 6-digit numeric string."""
        for _ in range(50):
            otp = generate_otp()
            self.assertEqual(len(otp), 6)
            self.assertTrue(otp.isdigit())

    @patch('appspark.views.send_notification_email')
    def test_workhand_registration_stores_hashed_password_in_session(self, mock_email):
        """Plaintext password must NEVER be saved in the session dict."""
        response = self.client.post(reverse('workhandregister'), {
            'username': 'johnny12',
            'email': 'johnny@example.com',
            'password': 'SecureP@ssword123',
            'fname': 'John',
            'lname': 'Doe',
            'category': self.category.id,
            'state': 'California',
            'city': 'San Francisco',
        })
        self.assertRedirects(response, reverse('verifyworkhandotp'))

        session = self.client.session
        pending = session.get('pending_workhand_registration')
        self.assertIsNotNone(pending)
        self.assertNotIn('password', pending)
        self.assertIn('password_hash', pending)
        self.assertTrue(pending['password_hash'].startswith('pbkdf2_') or 'sha' in pending['password_hash'])

    @patch('appspark.views.send_notification_email')
    def test_workhand_otp_verification_creates_user_and_can_login(self, mock_email):
        """Valid OTP creates the user with the hashed password; login works."""
        raw_pw = 'SuperSecret123!'
        self.client.post(reverse('workhandregister'), {
            'username': 'alice99',
            'email': 'alice@example.com',
            'password': raw_pw,
            'fname': 'Alice',
            'lname': 'Smith',
            'category': self.category.id,
        })
        pending = self.client.session.get('pending_workhand_registration')
        otp = pending['otp']

        verify_resp = self.client.post(reverse('verifyworkhandotp'), {'otp': otp})
        self.assertRedirects(verify_resp, reverse('workhandlogin'))

        # Check user created and session cleared
        user = User.objects.filter(username='alice99').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password(raw_pw))
        self.assertNotIn('pending_workhand_registration', self.client.session)

    @patch('appspark.views.send_notification_email')
    def test_otp_brute_force_lockout_terminates_session(self, mock_email):
        """Reaching MAX_OTP_ATTEMPTS failed guesses invalidates the pending registration."""
        self.client.post(reverse('workhandregister'), {
            'username': 'victim01',
            'email': 'victim@example.com',
            'password': 'Password123!',
            'fname': 'Vic',
            'lname': 'Tim',
            'category': self.category.id,
        })

        # Attempts 1 to 4 return 200 with remaining attempts warning
        for i in range(MAX_OTP_ATTEMPTS - 1):
            resp = self.client.post(reverse('verifyworkhandotp'), {'otp': '000000'})
            self.assertEqual(resp.status_code, 200)

        # 5th attempt locks out and redirects back to register
        locked_resp = self.client.post(reverse('verifyworkhandotp'), {'otp': '000000'})
        self.assertRedirects(locked_resp, reverse('workhandregister'))
        self.assertNotIn('pending_workhand_registration', self.client.session)
        self.assertFalse(User.objects.filter(username='victim01').exists())


class ProfileValidationTests(TestCase):
    def setUp(self):
        self.cat = WorkhandCategory.objects.create(category="Sound")
        self.u1 = User.objects.create_user('user1', 'u1@example.com', 'pass1')
        self.w1 = Workhand.objects.create(user=self.u1, workhand_category=self.cat)

        self.u2 = User.objects.create_user('user2', 'u2@example.com', 'pass2')
        self.w2 = Workhand.objects.create(user=self.u2, workhand_category=self.cat)

        self.co_user1 = User.objects.create_user('comp1', 'c1@example.com', 'pass1')
        self.co1 = Company.objects.create(user=self.co_user1, company_name='Company One')

        self.co_user2 = User.objects.create_user('comp2', 'c2@example.com', 'pass2')
        self.co2 = Company.objects.create(user=self.co_user2, company_name='Company Two')

    def test_workhand_profile_duplicate_username_prevented(self):
        """User cannot change their username to another user's username."""
        form = WorkhandProfileForm(
            data={
                'username': 'user2',  # belongs to u2
                'fname': 'User',
                'lname': 'One',
                'email': 'new_unique@example.com',
                'workhand_category': self.cat.id,
            },
            instance=self.w1,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertEqual(form.errors['username'], ['Username already exists.'])

    def test_workhand_profile_duplicate_email_prevented(self):
        """User cannot change their email to another user's email."""
        form = WorkhandProfileForm(
            data={
                'username': 'user1',
                'fname': 'User',
                'lname': 'One',
                'email': 'u2@example.com',  # belongs to u2
                'workhand_category': self.cat.id,
            },
            instance=self.w1,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertEqual(form.errors['email'], ['Email already registered by another account.'])

    def test_workhand_profile_keeping_own_credentials_is_valid(self):
        """Keeping own username and email passes validation."""
        form = WorkhandProfileForm(
            data={
                'username': 'user1',
                'fname': 'User',
                'lname': 'One',
                'email': 'u1@example.com',
                'workhand_category': self.cat.id,
            },
            instance=self.w1,
        )
        self.assertTrue(form.is_valid())

    def test_company_profile_duplicate_username_prevented(self):
        """Company cannot steal another user's username."""
        form = CompanyProfileForm(
            data={
                'username': 'comp2',
                'company_name': 'My Company',
                'email': 'newc@example.com',
            },
            instance=self.co1,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_file_size_validation_rejects_large_files(self):
        """Files larger than 5MB must be rejected by forms."""
        large_file = SimpleUploadedFile(
            'huge.jpg',
            b'x' * (MAX_UPLOAD_SIZE + 1024),
            content_type='image/jpeg',
        )
        form = WorkhandProfileForm(
            data={
                'username': 'user1',
                'fname': 'User',
                'lname': 'One',
                'email': 'u1@example.com',
                'workhand_category': self.cat.id,
            },
            files={'profile_pic': large_file},
            instance=self.w1,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('profile_pic', form.errors)


class HttpMethodSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = WorkhandCategory.objects.create(category="Sound")
        self.ecat = EventsCategory.objects.create(category="Concert")
        self.wh_user = User.objects.create_user('wh_guy', 'wh@example.com', 'pass123')
        self.wh = Workhand.objects.create(user=self.wh_user, workhand_category=self.cat)

        self.co_user = User.objects.create_user('co_owner', 'co@example.com', 'pass123')
        self.co = Company.objects.create(user=self.co_user, company_name='Sound Co')

        self.event = Event.objects.create(
            event_category=self.ecat,
            event_name="Live Concert",
            description="Loud music",
            start_date="2026-12-01",
            end_date="2026-12-02",
            workhand_category=self.cat,
            workhand_needed=2,
            payment_range=150.0,
            address="123 Music Ave",
            state="NY",
            city="NYC",
            company_id=self.co,
        )

    def test_apply_for_event_requires_post(self):
        """GET request to applyforevent must return HTTP 405 Method Not Allowed."""
        self.client.login(username='wh_guy', password='pass123')
        response = self.client.get(reverse('applyforevent', args=[self.event.id]))
        self.assertEqual(response.status_code, 405)
