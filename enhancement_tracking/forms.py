from django.forms import Form, ModelForm, CharField, IntegerField, PasswordInput
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
    """Form for changing the data of an existing user. All of the fields are set
    as not required. Changing the git_token and zen_token are handled in
    seperate forms."""
    class Meta:
        model = GZUserProfile
        exclude = ('user', 'git_token', 'zen_token')

#    def __init__(self, *args, **kwargs):
#        super(ProfileChangeForm, self).__init__(*args, **kwargs)
#        for key, field in self.fields.items():
#            self.fields[key].required = False
#    
#    # Override clean to remove the data from the fields that were left blank
#    def clean(self):
#        super(ProfileChangeForm, self).clean()
#        data = self.cleaned_data
#        for key, field in data.items():
#            if data[key] is None or data[key] == '':
#                del data[key]
#
#        return data

class ZendeskTokenChangeForm(ModelForm):
    """Form for changing the Zendesk API Token of an existing user."""
    class Meta:
        model = GZUserProfile
        fields = ('zen_token',)
        widgets = {
            'zen_token': PasswordInput()
        }
