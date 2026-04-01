from django import forms
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from .models import User, Visitor, Visit, Blacklist


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username', 'id': 'id_username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password', 'id': 'id_password'})
    )


class VisitorForm(forms.ModelForm):
    class Meta:
        model = Visitor
        fields = ['name', 'email', 'phone', 'company', 'address', 'id_proof_type', 'id_proof_number', 'photo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email Address'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone Number'}),
            'company': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Company / Organization'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Address', 'rows': 2}),
            'id_proof_type': forms.Select(attrs={'class': 'form-input'}),
            'id_proof_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'ID Proof Number'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-input'}),
        }


class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['host', 'purpose', 'badge_number']
        widgets = {
            'host': forms.Select(attrs={'class': 'form-input'}),
            'purpose': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Purpose of Visit'}),
            'badge_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Badge Number'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['host'].queryset = User.objects.filter(role='employee')
        self.fields['host'].label = 'Select Host (Employee)'


class UserCreateForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'phone', 'department']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email'}),
            'role': forms.Select(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone'}),
            'department': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Department'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Confirm Password'})


class BlacklistForm(forms.ModelForm):
    class Meta:
        model = Blacklist
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Reason for blacklisting', 'rows': 3}),
        }
