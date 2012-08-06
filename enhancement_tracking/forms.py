from django.forms import (
    Form, ModelForm, CharField, IntegerField, ModelChoiceField, RegexField,
    EmailField, PasswordInput
)
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from enhancement_tracking.models import UserProfile, APIAccessData

class GroupSuperuserForm(UserCreationForm):
    """Form for creating a new group superuser. Extends django's provided
    UserForm, but removes the help_text and relabels some of the fields so that
    the user knows they are creating the group superuser."""
    def __init__(self, *args, **kwargs):
        super(GroupSuperuserForm, self).__init__(*args, **kwargs)
        self.fields['username'].help_text = ''
        self.fields['username'].label = 'Group Superuser Username'
        self.fields['password2'].help_text = ''
        self.fields['password2'].label = 'Password Confirmation'

class APIAccessDataForm(ModelForm):
    """Form for creating a set of access data for the GitHub and Zendesk
    APIs."""
    class Meta:
        model = APIAccessData
        exclude = ('git_token')
        widgets = {
            'zen_token': PasswordInput()
        }

class NewUserForm(Form):
    """Form for getting a username and email for the creation of a new user.
    This form does not create the user by itself, but just gets the information
    necessary to create a new user account for a group.

    This form uses code from django's default UserCreationForm.
    """
    error_messages = {
        'duplicate_username': "A user with that username already exists.",
    }
    username = RegexField(label='Username', max_length=30,
        regex=r'^[\w.@+-]+$',
        error_messages = {
            'invalid': "This value may contain only letters, numbers and " \
                       "@/./+/-/_ characters."
        }
    )
    email = EmailField(label='Email')

    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM.
        username = self.cleaned_data["username"]
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])

class UserProfileForm(ModelForm):
    """Form to set the two editable fields of a user's profile data."""
    class Meta:
        model = UserProfile
        fields = ('utc_offset', 'view_type')

class ActiveUserSelectionForm(Form):
    """Form for selecting a specific GitZen user's profile. Excludes
    superusers and users who are set as inactive.""" 
    user = ModelChoiceField(queryset=User.objects.\
                            exclude(is_superuser=True).exclude(is_active=False),
                            label='Select User')

class InactiveUserSelectionForm(Form):
    """Form for selecting a specific GitZen user's profile. Excludes superusers
    and users who are set as active."""
    user = ModelChoiceField(queryset=User.objects.\
                            exclude(is_superuser=True).exclude(is_active=True),
                            label='Select User')
