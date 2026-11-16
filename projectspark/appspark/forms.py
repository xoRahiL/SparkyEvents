from django import forms
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from .models import (
    Workhand, WorkhandCategory, Company, Event,
    EventsCategory, Feedback,
)

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB


# ---------- Shared mixin for the "register" forms ----------
class BaseRegisterForm(forms.Form):
    """Common fields + validation shared by Workhand and Company registration."""
    username = forms.CharField(max_length=50)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    propic = forms.ImageField(required=False)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if not username.isalnum():
            raise forms.ValidationError('Username should be alpha-numeric only, no spaces or symbols.')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email already exists.')
        return email

    def clean_propic(self):
        pic = self.cleaned_data.get('propic')
        if isinstance(pic, UploadedFile) and pic.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError('Profile picture cannot exceed 5MB.')
        return pic


class WorkhandRegisterForm(BaseRegisterForm):
    fname = forms.CharField(max_length=50)
    lname = forms.CharField(max_length=50)
    category = forms.ModelChoiceField(queryset=WorkhandCategory.objects.all())
    state = forms.CharField(max_length=50, required=False)
    city = forms.CharField(max_length=50, required=False)


class CompanyRegisterForm(BaseRegisterForm):
    cname = forms.CharField(max_length=50)
    state = forms.CharField(max_length=50, required=False)
    city = forms.CharField(max_length=50, required=False)


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


# ---------- Profile forms (ModelForms, closer to the real schema) ----------
class WorkhandProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=50)
    fname = forms.CharField(max_length=50)
    lname = forms.CharField(max_length=50)
    email = forms.EmailField()

    class Meta:
        model = Workhand
        fields = ['profile_pic', 'contact', 'address', 'state', 'city', 'workhand_category']

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if not username.isalnum():
            raise forms.ValidationError('Username should be alpha-numeric only.')
        current_user_id = self.instance.user_id if self.instance and self.instance.pk else None
        if User.objects.filter(username__iexact=username).exclude(pk=current_user_id).exists():
            raise forms.ValidationError('Username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        current_user_id = self.instance.user_id if self.instance and self.instance.pk else None
        if User.objects.filter(email__iexact=email).exclude(pk=current_user_id).exists():
            raise forms.ValidationError('Email already registered by another account.')
        return email

    def clean_profile_pic(self):
        pic = self.cleaned_data.get('profile_pic')
        if isinstance(pic, UploadedFile) and pic.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError('Profile picture cannot exceed 5MB.')
        return pic


class CompanyProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=50)
    company_name = forms.CharField(max_length=50)
    email = forms.EmailField()

    class Meta:
        model = Company
        fields = ['profile_pic', 'contact', 'address', 'state', 'city']

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if not username.isalnum():
            raise forms.ValidationError('Username should be alpha-numeric only.')
        current_user_id = self.instance.user_id if self.instance and self.instance.pk else None
        if User.objects.filter(username__iexact=username).exclude(pk=current_user_id).exists():
            raise forms.ValidationError('Username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        current_user_id = self.instance.user_id if self.instance and self.instance.pk else None
        if User.objects.filter(email__iexact=email).exclude(pk=current_user_id).exists():
            raise forms.ValidationError('Email already registered by another account.')
        return email

    def clean_profile_pic(self):
        pic = self.cleaned_data.get('profile_pic')
        if isinstance(pic, UploadedFile) and pic.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError('Profile picture cannot exceed 5MB.')
        return pic


# ---------- Event forms ----------
class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'event_category', 'event_name', 'description', 'start_date', 'end_date',
            'workhand_category', 'workhand_needed', 'payment_range',
            'address', 'state', 'city',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('start_date'), cleaned.get('end_date')
        if start and end and end < start:
            raise forms.ValidationError('End date cannot be before start date.')
        return cleaned


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['feedback_title', 'feedback']
