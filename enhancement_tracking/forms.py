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
    """User profile form for creating a new user."""
    class Meta:
        model = GZUserProfile
        exclude = ('user',)
        widgets = {
            'git_pass': PasswordInput(),
            'zen_token': PasswordInput()
        }

class ChangeForm(Form):
    """Form for changing the data of an existing user. Does not use ModelForm
    because all of the fields need to be set as not required."""
    old_pass = CharField(max_length=75, widget=PasswordInput, required=False)
    new_pass = CharField(max_length=75, widget=PasswordInput, required=False)
    aff_pass = CharField(max_length=75, widget=PasswordInput, required=False)
    git_name = CharField(max_length=75, required=False)
    git_pass = CharField(max_length=75, widget=PasswordInput, required=False)
    git_org = CharField(max_length=75, required=False)
    git_repo = CharField(max_length=75, required=False)
    zen_name = CharField(max_length=75, required=False)
    zen_token = CharField(max_length=75, widget=PasswordInput, required=False)
    zen_url = CharField(max_length=100, required=False)
    zen_fieldid = IntegerField(required=False)
    age_limit = IntegerField(required=False)