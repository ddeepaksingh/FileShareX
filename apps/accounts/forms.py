from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'profile_photo']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', "Passwords do not match.")
        if pw:
            try:
                validate_password(pw, self.instance)
            except forms.ValidationError as e:
                self.add_error('password', e)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email address'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    remember_me = forms.BooleanField(required=False)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get('email', '').lower()
        password = cleaned.get('password', '')
        if email and password:
            self.user = authenticate(self.request, username=email, password=password)
            if self.user is None:
                raise forms.ValidationError("Invalid email or password.")
            if not self.user.is_active:
                raise forms.ValidationError("This account has been deactivated.")
        return cleaned

    def get_user(self):
        return self.user


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'profile_photo', 'email_notifications']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters.")
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This username is taken.")
        return username
