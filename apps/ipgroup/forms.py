from django import forms
from django.conf import settings


EXPIRY_CHOICES = [
    ('1h',  '1 hour'),
    ('24h', '24 hours (default)'),
    ('7d',  '7 days'),
]


class IPGroupUploadForm(forms.Form):
    file = forms.FileField(
        label='File',
        widget=forms.FileInput(attrs={'class': 'form-control'}),
    )
    title = forms.CharField(
        max_length=255,
        required=False,
        label='Title',
        widget=forms.TextInput(attrs={'placeholder': 'Leave blank to use filename'}),
    )
    description = forms.CharField(
        required=False,
        label='Description',
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional description…'}),
    )
    expiry = forms.ChoiceField(
        choices=EXPIRY_CHOICES,
        initial='24h',
        label='Auto-delete after',
    )

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f:
            max_mb = getattr(settings, 'IP_GROUP_MAX_UPLOAD_MB', 50)
            if f.size > max_mb * 1024 * 1024:
                raise forms.ValidationError(
                    f"File exceeds the {max_mb} MB limit for IP sharing."
                )
        return f
