from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import password_validation

class UserRegisterForm(UserCreationForm):
    """
    Form for registering a new user, requiring a strong password and unique email address.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'you@example.com'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Last Name'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            # Clear default helper texts / instructions
            field.help_text = None

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password1')
        
        # Instantiate dummy User object for security checks
        user = User(
            username=cleaned_data.get('username'),
            email=cleaned_data.get('email'),
            first_name=cleaned_data.get('first_name'),
            last_name=cleaned_data.get('last_name')
        )
        
        if password:
            try:
                password_validation.validate_password(password, user)
            except forms.ValidationError as error:
                self.add_error('password1', error)
                
        return cleaned_data


class UserLoginForm(AuthenticationForm):
    """
    Custom login form that raises validation error if username is not registered.
    """
    def clean(self):
        username = self.cleaned_data.get('username')
        if username and not User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is not registered. Please register first.")
        return super().clean()


class EmailForm(forms.Form):
    """
    Form for composing a tracked email.
    The message field is populated by the Quill.js editor on submission.
    """
    recipient = forms.EmailField(
        label="Recipient Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'recipient@example.com',
            'id': 'recipient-field'
        })
    )
    subject = forms.CharField(
        max_length=255,
        label="Subject",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email subject...',
            'id': 'subject-field'
        })
    )
    message = forms.CharField(
        widget=forms.HiddenInput(attrs={
            'id': 'message-field'
        })
    )

    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        # Prevent HTTP/Email header splitting attacks
        if '\r' in subject or '\n' in subject:
            raise forms.ValidationError("Subject line must not contain carriage return or line break characters.")
        return subject

