# Phase 1: Core User System — Feature Specification

**Phase:** 1 of 6  
**Feature Area:** Authentication, User Profile & Password Management  
**Estimated Time:** 1–2 days  
**Status:** Ready for Implementation  
**Date:** May 2026

---

## Scope

This phase delivers the complete user identity layer. Every subsequent phase depends on it.

**Included:**
- Django project scaffolding
- Custom User model
- Signup (registration)
- Login / Logout
- User Profile & Dashboard (basic)
- Password change & reset
- Base template + Navbar
- Django Admin configuration

**Not included in this phase:**
- File upload (Phase 2)
- Groups (Phase 4)
- IP Group / anonymous sharing (Phase 3)
- Notifications (Phase 6)

---

## Project Structure to Create

```
file_sharing_platform/
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   └── accounts/
│       ├── migrations/
│       ├── __init__.py
│       ├── models.py
│       ├── views.py
│       ├── forms.py
│       ├── urls.py
│       ├── admin.py
│       ├── signals.py
│       └── tests/
│           ├── __init__.py
│           ├── test_models.py
│           └── test_views.py
│
├── templates/
│   ├── base.html
│   ├── components/
│   │   ├── navbar.html
│   │   └── messages.html
│   └── accounts/
│       ├── signup.html
│       ├── login.html
│       ├── profile.html
│       ├── dashboard.html
│       ├── password_change.html
│       ├── password_reset.html
│       ├── password_reset_confirm.html
│       └── password_reset_done.html
│
├── static/
│   ├── css/
│   │   └── main.css
│   └── js/
│       └── main.js
│
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── pytest.ini
└── .env.example
```

---

## 1. Custom User Model

**File:** `apps/accounts/models.py`

### Model Definition

```python
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True)
    storage_quota = models.BigIntegerField(default=5_368_709_120)  # 5 GB
    storage_used = models.BigIntegerField(default=0)
    email_notifications = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
        ]

    def storage_quota_display(self):
        return self._bytes_to_human(self.storage_quota)

    def storage_used_display(self):
        return self._bytes_to_human(self.storage_used)

    def storage_used_percent(self):
        if self.storage_quota == 0:
            return 0
        return round((self.storage_used / self.storage_quota) * 100, 1)

    @staticmethod
    def _bytes_to_human(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
```

### Settings Required

```python
# config/settings/base.py
AUTH_USER_MODEL = 'accounts.User'
```

> **Critical:** `AUTH_USER_MODEL` must be set before the first migration. Changing it later requires recreating the database.

---

## 2. Signup

### URL
`POST /accounts/signup/`

### Form: `SignupForm`

**File:** `apps/accounts/forms.py`

```python
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'profile_photo']

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")
        if pw:
            validate_password(pw)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
        return user
```

### View: `SignupView`

**File:** `apps/accounts/views.py`

```python
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views import View

from .forms import SignupForm


class SignupView(View):
    template_name = 'accounts/signup.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        return render(request, self.template_name, {'form': SignupForm()})

    def post(self, request):
        form = SignupForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('accounts:dashboard')
        return render(request, self.template_name, {'form': form})
```

### Validation Rules

| Field | Rule |
|-------|------|
| `username` | Required, unique (case-insensitive), 3–150 chars, alphanumeric + `_.-` |
| `email` | Required, unique (case-insensitive), valid email format |
| `password` | Django's `AUTH_PASSWORD_VALIDATORS` (min 8 chars, not entirely numeric, not too common) |
| `confirm_password` | Must match `password` |
| `profile_photo` | Optional, image files only, max 5 MB |

### Post-Signup Behaviour
- User is automatically logged in after successful signup
- Redirected to dashboard
- Profile photo stored under `media/profiles/`

---

## 3. Login

### URL
`POST /accounts/login/`

### Form: `LoginForm`

```python
from django import forms
from django.contrib.auth import authenticate


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    remember_me = forms.BooleanField(required=False)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email', '').lower()
        password = self.cleaned_data.get('password', '')
        if email and password:
            self.user = authenticate(self.request, username=email, password=password)
            if self.user is None:
                raise forms.ValidationError("Invalid email or password.")
            if not self.user.is_active:
                raise forms.ValidationError("This account has been deactivated.")
        return self.cleaned_data

    def get_user(self):
        return self.user
```

### View: `LoginView`

```python
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views import View

from .forms import LoginForm

SESSION_EXPIRY_REMEMBER = 60 * 60 * 24 * 30   # 30 days
SESSION_EXPIRY_DEFAULT = 0                       # Browser session


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        return render(request, self.template_name, {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request, request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if form.cleaned_data.get('remember_me'):
                request.session.set_expiry(SESSION_EXPIRY_REMEMBER)
            else:
                request.session.set_expiry(SESSION_EXPIRY_DEFAULT)
            next_url = request.GET.get('next', 'accounts:dashboard')
            return redirect(next_url)
        return render(request, self.template_name, {'form': form})
```

### Behaviour
- Login by **email** (not username) — `USERNAME_FIELD = 'email'`
- `remember_me` checked → 30-day session; unchecked → browser session
- Respects `?next=` redirect parameter
- Failed logins show a generic message (no enumeration of valid emails)

---

## 4. Logout

### URL
`POST /accounts/logout/`  (POST only — protects against CSRF-triggered logout)

```python
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views import View


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('accounts:login')
```

---

## 5. User Profile

### URL
`GET /accounts/profile/`  
`POST /accounts/profile/` (update)

### Form: `ProfileUpdateForm`

```python
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'profile_photo', 'email_notifications']

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This username is taken.")
        return username
```

### View: `ProfileView`

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from .forms import ProfileUpdateForm


class ProfileView(LoginRequiredMixin, View):
    template_name = 'accounts/profile.html'

    def get(self, request):
        form = ProfileUpdateForm(instance=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ProfileUpdateForm(
            request.POST, request.FILES, instance=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('accounts:profile')
        return render(request, self.template_name, {'form': form})
```

### Profile Page Displays
- Profile photo (with fallback avatar)
- Username and email
- Storage usage bar: `X MB used of Y GB`
- Total files count
- Member since date
- Email notification toggle
- Links to: Change Password, My Files (Phase 2), My Groups (Phase 4)

---

## 6. Dashboard

### URL
`GET /accounts/dashboard/`

```python
class DashboardView(LoginRequiredMixin, View):
    template_name = 'accounts/dashboard.html'

    def get(self, request):
        context = {
            'storage_used': request.user.storage_used,
            'storage_quota': request.user.storage_quota,
            'storage_percent': request.user.storage_used_percent(),
            # files / groups populated in Phase 2+
        }
        return render(request, self.template_name, context)
```

---

## 7. Password Management

### 7a. Password Change (logged-in user)

**URL:** `GET/POST /accounts/password/change/`

Uses Django's built-in `PasswordChangeView` with a custom template:

```python
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy


class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')
```

Form fields: current password, new password, confirm new password.  
On success: session is updated so the user stays logged in (Django handles this automatically via `update_session_auth_hash`).

### 7b. Password Reset (forgot password)

**Flow:**
```
/accounts/password/reset/          ← user enters email
/accounts/password/reset/done/     ← "check your email" confirmation
/accounts/password/reset/<uidb64>/<token>/  ← link from email
/accounts/password/reset/complete/ ← success page
```

Uses Django's built-in class-based views with custom templates:

```python
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

urlpatterns = [
    path('password/reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/emails/password_reset.txt',
             success_url=reverse_lazy('accounts:password_reset_done'),
         ),
         name='password_reset'),

    path('password/reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html',
         ),
         name='password_reset_done'),

    path('password/reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url=reverse_lazy('accounts:password_reset_complete'),
         ),
         name='password_reset_confirm'),

    path('password/reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_done.html',
         ),
         name='password_reset_complete'),
]
```

**Security notes:**
- Reset link is single-use (Django invalidates token after use)
- Token expires after `PASSWORD_RESET_TIMEOUT` seconds (default 3 days; set to 86400 = 1 day in settings)
- Email is sent regardless of whether the address exists (prevents email enumeration)

---

## 8. URL Configuration

**File:** `apps/accounts/urls.py`

```python
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('password/change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    # Password reset URLs listed above
]
```

**File:** `config/urls.py`

```python
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## 9. Admin Configuration

**File:** `apps/accounts/admin.py`

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'is_active', 'is_staff', 'date_joined', 'storage_used_display']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['email', 'username']
    ordering = ['-date_joined']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Storage', {'fields': ('storage_quota', 'storage_used')}),
        ('Settings', {'fields': ('profile_photo', 'email_notifications')}),
    )
```

---

## 10. Base Template & Navbar

**File:** `templates/base.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}FileShare{% endblock %}</title>
    {% load static %}
    <link rel="stylesheet" href="{% static 'css/main.css' %}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% include "components/navbar.html" %}
    {% include "components/messages.html" %}

    <main class="container mx-auto px-4 py-6">
        {% block content %}{% endblock %}
    </main>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

**File:** `templates/components/navbar.html`

```html
{% load static %}
<nav>
    <a href="{% url 'accounts:dashboard' %}">FileShare</a>
    
    {% if user.is_authenticated %}
        <a href="{% url 'accounts:dashboard' %}">Dashboard</a>
        <a href="{% url 'accounts:profile' %}">{{ user.username }}</a>
        <form method="post" action="{% url 'accounts:logout' %}">
            {% csrf_token %}
            <button type="submit">Logout</button>
        </form>
    {% else %}
        <a href="{% url 'accounts:login' %}">Login</a>
        <a href="{% url 'accounts:signup' %}">Sign Up</a>
    {% endif %}
</nav>
```

---

## 11. Settings Configuration

**File:** `config/settings/base.py` (accounts-relevant portion)

```python
AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

PASSWORD_RESET_TIMEOUT = 86400  # 1 day

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # dev only
```

---

## 12. Requirements

**File:** `requirements/base.txt`

```
Django>=4.2,<5.0
Pillow>=10.0          # profile photo / ImageField
psycopg2-binary>=2.9  # PostgreSQL adapter
python-decouple>=3.8  # .env loading
```

**File:** `requirements/development.txt`

```
-r base.txt
pytest>=7.4
pytest-django>=4.7
factory-boy>=3.3      # test fixtures
```

---

## 13. Testing Requirements

**File:** `apps/accounts/tests/test_views.py`

### Signup Tests
- `test_signup_valid` — creates user, logs in, redirects to dashboard
- `test_signup_duplicate_email` — form error returned
- `test_signup_duplicate_username_case_insensitive` — rejects `Admin` when `admin` exists
- `test_signup_password_mismatch` — form error returned
- `test_signup_weak_password` — form error returned

### Login Tests
- `test_login_valid_email` — success + redirect to dashboard
- `test_login_invalid_password` — generic error, no user enumeration
- `test_login_inactive_user` — rejected with appropriate message
- `test_login_remember_me_sets_long_session`
- `test_login_respects_next_param`

### Profile Tests
- `test_profile_requires_login` — anonymous → redirect to login
- `test_profile_update_email` — success
- `test_profile_update_duplicate_email` — form error
- `test_profile_photo_upload`

### Password Tests
- `test_password_change_success` — old + new + confirm
- `test_password_change_wrong_current` — form error
- `test_password_reset_email_sent`
- `test_password_reset_confirm_sets_new_password`

### Model Tests
- `test_storage_used_percent_calculation`
- `test_bytes_to_human_formatting`

---

## 14. Security Checklist for This Phase

- [ ] `AUTH_USER_MODEL` set before any migrations
- [ ] `email` is `USERNAME_FIELD` — login by email, not username
- [ ] Passwords stored with Django's PBKDF2 hasher (default)
- [ ] CSRF token on all POST forms (login, logout, profile update)
- [ ] Logout via POST only (not GET)
- [ ] `LoginRequiredMixin` on all authenticated views
- [ ] No email enumeration in login error messages
- [ ] No email enumeration in password reset flow
- [ ] Profile photo validated as image (Pillow's `ImageField` handles this)
- [ ] `PASSWORD_RESET_TIMEOUT = 86400` (1 day, not default 3 days)
- [ ] `update_session_auth_hash` called on password change (built into Django's view)

---

## 15. Implementation Order

Follow this order to avoid import or migration issues:

1. Create Django project: `django-admin startproject config .`
2. Create accounts app: `python manage.py startapp accounts apps/accounts`
3. Add `AUTH_USER_MODEL = 'accounts.User'` to `settings/base.py`
4. Define `User` model in `accounts/models.py`
5. Run `python manage.py makemigrations accounts` → `python manage.py migrate`
6. Create `UserAdmin` in `accounts/admin.py`
7. Implement forms (`SignupForm`, `LoginForm`, `ProfileUpdateForm`)
8. Implement views (Signup → Login → Logout → Profile → Dashboard → Password)
9. Wire up `accounts/urls.py` and `config/urls.py`
10. Create `base.html`, `navbar.html`, and all account templates
11. Run `python manage.py createsuperuser` to verify admin works
12. Write and run tests

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| 1 | A new user can sign up with email + username + password |
| 2 | Duplicate email or username is rejected with a clear error |
| 3 | User is auto-logged in after signup |
| 4 | User can log in with email + password |
| 5 | "Remember me" keeps session for 30 days |
| 6 | User can log out via the navbar button |
| 7 | Profile page shows storage bar, username, email |
| 8 | User can update username, email, profile photo |
| 9 | User can change password while logged in |
| 10 | User can reset password via email link |
| 11 | All authenticated views redirect unauthenticated users to login |
| 12 | Django admin lists users with email search |
| 13 | All tests pass: `pytest apps/accounts/` |
