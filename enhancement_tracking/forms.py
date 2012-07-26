from django.forms import ModelForm, CharField, IntegerField, PasswordInput
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from enhancement_tracking.models import GZUserProfile

class UserForm(UserCreationForm):
    """User form for creating a new user. Extends django's provided
    UserCreationForm, but removes the help_text from the fields."""
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['username'].help_text = ''
        self.fields['password2'].help_text = ''
        self.fields['password2'].label = 'Password Confirmation'

class UserProfileForm(ModelForm):
    """User profile form for adding data to a new user's profile."""
    class Meta:
        model = GZUserProfile
        exclude = ('user', 'git_token')
        widgets = {
            'zen_token': PasswordInput()
        }

class ProfileChangeForm(ModelForm):
    """Form for changing the profile data of an existing user. All of the fields
    have their intial values set at the field's value for the current user's
    profile. Changing the git_token and zen_token are handled in seperate
    forms."""
    class Meta:
        model = GZUserProfile
        exclude = ('user', 'git_token', 'zen_token')

class ZendeskTokenChangeForm(ModelForm):
    """Form for changing the Zendesk API Token of an existing user."""
    class Meta:
        model = GZUserProfile
        fields = ('zen_token',)
        widgets = {
            'zen_token': PasswordInput()
        }
