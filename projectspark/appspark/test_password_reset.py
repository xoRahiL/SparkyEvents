"""Tests for the email password-reset flow and the loading-indicator script tag.

Run with:  python manage.py test appspark
"""
import re
import time
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from appspark import views
from appspark.models import Company, Workhand, WorkhandCategory

# Independent of Cloudinary / env vars: pages that show profile pictures work in tests.
TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

LINK_RE = re.compile(r'https?://\S+/(?:workhand|company)reset/\S+/')


@override_settings(STORAGES=TEST_STORAGES)
class ResetBase(TestCase):
    OLD = 'OldPassw0rd!x'
    NEW = 'Brand-New-Pass-742'

    def setUp(self):
        cache.clear()
        category = WorkhandCategory.objects.first() or WorkhandCategory.objects.create(category='Test')
        self.wh_user = User.objects.create_user('wh1', 'wh@example.com', self.OLD, first_name='Wendy')
        Workhand.objects.create(user=self.wh_user, workhand_category=category)
        self.co_user = User.objects.create_user('co1', 'co@example.com', self.OLD, first_name='Cody')
        Company.objects.create(user=self.co_user, company_name='Co Ltd')

        patcher = mock.patch('appspark.views.send_notification_email')
        self.mail = patcher.start()
        self.addCleanup(patcher.stop)

    # helpers
    def request_reset(self, role, email, **kwargs):
        return self.client.post(reverse(f'{role}forget'), {'email': email}, **kwargs)

    def last_link(self):
        subject, message, to_email = self.mail.call_args[0]
        match = LINK_RE.search(message)
        self.assertIsNotNone(match, f'no reset link in email: {message!r}')
        return match.group(0)

    def token_from(self, link):
        return link.rstrip('/').split('/')[-1]


class RequestResetTests(ResetBase):
    def test_forgot_pages_ask_only_for_email(self):
        for role in ('workhand', 'company'):
            html = self.client.get(reverse(f'{role}forget')).content.decode()
            self.assertIn('name="email"', html)
            self.assertNotIn('name="security"', html)   # old insecure "college name" question is gone
            self.assertNotIn('name="password"', html)
            self.assertIn('js/loader.js', html)

    def test_known_email_gets_one_email_with_working_link(self):
        response = self.request_reset('workhand', 'wh@example.com')
        self.assertRedirects(response, reverse('workhandlogin'))
        self.mail.assert_called_once()
        subject, message, to_email = self.mail.call_args[0]
        self.assertEqual(to_email, 'wh@example.com')
        self.assertIn('Reset', subject)
        self.assertIn('60 minutes', message)
        self.assertEqual(self.client.get(self.last_link()).status_code, 200)

    def test_email_match_is_case_insensitive(self):
        self.request_reset('workhand', 'WH@Example.COM')
        self.mail.assert_called_once()

    def test_unknown_email_gets_identical_response_and_no_email(self):
        known = self.request_reset('workhand', 'wh@example.com', follow=True)
        known_msgs = [m.message for m in known.context['messages']]
        self.mail.reset_mock()
        cache.clear()
        unknown = self.request_reset('workhand', 'nobody@example.com', follow=True)
        unknown_msgs = [m.message for m in unknown.context['messages']]
        self.mail.assert_not_called()
        self.assertEqual(known_msgs, unknown_msgs)          # cannot be used to find out who has an account
        self.assertEqual(known.redirect_chain, unknown.redirect_chain)

    def test_roles_are_isolated(self):
        self.request_reset('workhand', 'co@example.com')    # a company email on the workhand page
        self.request_reset('company', 'wh@example.com')     # and the other way round
        self.mail.assert_not_called()

    def test_company_flow_sends_company_link(self):
        self.request_reset('company', 'co@example.com')
        self.assertIn('/companyreset/', self.last_link())

    def test_repeat_requests_within_a_minute_send_one_email(self):
        self.request_reset('workhand', 'wh@example.com')
        self.request_reset('workhand', 'wh@example.com')
        self.request_reset('workhand', 'WH@example.com')
        self.assertEqual(self.mail.call_count, 1)

    def test_inactive_account_gets_nothing(self):
        self.wh_user.is_active = False
        self.wh_user.save()
        self.request_reset('workhand', 'wh@example.com')
        self.mail.assert_not_called()

    @override_settings(IS_PRODUCTION=True)
    def test_link_uses_https_in_production(self):
        self.request_reset('workhand', 'wh@example.com')
        self.assertTrue(self.last_link().startswith('https://'))


class SetNewPasswordTests(ResetBase):
    def start(self, role='workhand', email='wh@example.com'):
        self.request_reset(role, email)
        link = self.last_link()
        self.mail.reset_mock()
        return link

    def test_full_flow_changes_password_and_sends_confirmation(self):
        link = self.start()
        page = self.client.get(link)
        self.assertEqual(page.status_code, 200)
        self.assertTemplateUsed(page, 'reset_password.html')
        self.assertIn('no-referrer', page.content.decode())   # token must not leak via Referer

        response = self.client.post(link, {'new_password1': self.NEW, 'new_password2': self.NEW})
        self.assertRedirects(response, reverse('workhandlogin'))

        self.assertTrue(self.client.login(username='wh1', password=self.NEW))
        self.client.logout()
        self.assertFalse(self.client.login(username='wh1', password=self.OLD))

        self.mail.assert_called_once()
        subject, message, to_email = self.mail.call_args[0]
        self.assertEqual(to_email, 'wh@example.com')
        self.assertIn('password was changed', subject)

    def test_company_full_flow(self):
        link = self.start('company', 'co@example.com')
        response = self.client.post(link, {'new_password1': self.NEW, 'new_password2': self.NEW})
        self.assertRedirects(response, reverse('companylogin'))
        self.assertTrue(self.client.login(username='co1', password=self.NEW))

    def test_link_can_only_be_used_once(self):
        link = self.start()
        self.client.post(link, {'new_password1': self.NEW, 'new_password2': self.NEW})
        again = self.client.get(link)
        self.assertRedirects(again, reverse('workhandforget'))
        second = self.client.post(link, {'new_password1': 'Another-Pass-9981', 'new_password2': 'Another-Pass-9981'})
        self.assertRedirects(second, reverse('workhandforget'))
        self.assertTrue(self.client.login(username='wh1', password=self.NEW))   # unchanged by the 2nd attempt

    def test_mismatched_passwords_change_nothing(self):
        link = self.start()
        response = self.client.post(link, {'new_password1': self.NEW, 'new_password2': self.NEW + 'x'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.login(username='wh1', password=self.OLD))
        self.mail.assert_not_called()

    def test_weak_password_is_rejected_by_django_validators(self):
        link = self.start()
        response = self.client.post(link, {'new_password1': '123', 'new_password2': '123'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.login(username='wh1', password=self.OLD))

    def test_token_expires_after_one_hour(self):
        token = views.make_reset_token(self.wh_user, 'workhand')
        now = time.time()
        with mock.patch('time.time', return_value=now + 3500):
            self.assertEqual(views.read_reset_token(token, 'workhand'), self.wh_user)
        with mock.patch('time.time', return_value=now + 3700):
            self.assertIsNone(views.read_reset_token(token, 'workhand'))

    def test_token_from_one_role_is_useless_for_the_other(self):
        token = views.make_reset_token(self.wh_user, 'workhand')
        response = self.client.get(reverse('companyreset', args=[token]))
        self.assertRedirects(response, reverse('companyforget'))

    def test_garbage_and_tampered_tokens_are_rejected(self):
        good = views.make_reset_token(self.wh_user, 'workhand')
        for bad in ('garbage', 'a:b:c', good + 'x', good[:-3], good.replace(':', '', 1)):
            self.assertIsNone(views.read_reset_token(bad, 'workhand'), bad)
            response = self.client.get(reverse('workhandreset', args=[bad]))
            self.assertRedirects(response, reverse('workhandforget'))

    def test_token_dies_when_account_is_deactivated(self):
        token = views.make_reset_token(self.wh_user, 'workhand')
        self.wh_user.is_active = False
        self.wh_user.save()
        self.assertIsNone(views.read_reset_token(token, 'workhand'))


class ChangePasswordEmailTests(ResetBase):
    def test_workhand_change_password_sends_notice(self):
        self.client.force_login(self.wh_user)
        self.client.post(reverse('workhandchangepassword'), {
            'old_password': self.OLD, 'new_password1': self.NEW, 'new_password2': self.NEW,
        })
        self.mail.assert_called_once()
        self.assertEqual(self.mail.call_args[0][2], 'wh@example.com')

    def test_company_change_password_sends_notice(self):
        self.client.force_login(self.co_user)
        self.client.post(reverse('companychangepassword'), {
            'old_password': self.OLD, 'new_password1': self.NEW, 'new_password2': self.NEW,
        })
        self.mail.assert_called_once()
        self.assertEqual(self.mail.call_args[0][2], 'co@example.com')

    def test_wrong_old_password_sends_nothing(self):
        self.client.force_login(self.wh_user)
        self.client.post(reverse('workhandchangepassword'), {
            'old_password': 'wrong', 'new_password1': self.NEW, 'new_password2': self.NEW,
        })
        self.mail.assert_not_called()


class LoaderIncludedTests(ResetBase):
    def assertHasLoader(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertIn('js/loader.js', response.content.decode())

    def test_public_pages(self):
        for url in ('/', reverse('workhandlogin'), reverse('companylogin'),
                    reverse('workhandforget'), reverse('companyforget')):
            self.assertHasLoader(self.client.get(url))

    def test_reset_page(self):
        self.request_reset('workhand', 'wh@example.com')
        self.assertHasLoader(self.client.get(self.last_link()))

    def test_otp_pages(self):
        session = self.client.session
        session['pending_workhand_registration'] = {'email': 'x@example.com'}
        session['pending_company_registration'] = {'email': 'y@example.com'}
        session.save()
        self.assertHasLoader(self.client.get(reverse('verifyworkhandotp')))
        self.assertHasLoader(self.client.get(reverse('verifycompanyotp')))

    def test_dashboards_and_inner_pages(self):
        self.client.force_login(self.wh_user)
        for name in ('workhanddashboard', 'searchevents', 'approved', 'workhandprofile', 'workhandeventhistory'):
            self.assertHasLoader(self.client.get(reverse(name)))
        self.client.force_login(self.co_user)
        for name in ('companydashboard', 'manageevent', 'approveapplications', 'companyprofile', 'companyeventhistory'):
            self.assertHasLoader(self.client.get(reverse(name)))
