
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import (
    CharField,
    EmailField,
    Form,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    PasswordInput,
    RegexField,
)

from gitzen.enhancement_tracking.models import UserProfile, APIAccessData

class NewUserForm(Form):
    """Form for getting a username and email for the creation of a new user.
    This form does not create the user by itself, but just gets the information
    necessary to create a new user account for a group.

    This form uses code from django's default UserCreationForm.
    """
    error_messages = {
        'duplicate_username': "A user with that username already exists.",
    }
    username = RegexField(label='Username', max_length=30, regex=r'^[\w.@+-]+$',
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

class NewGroupSuperuserForm(UserCreationForm):
    """Form for creating a new group superuser. Extends django's provided
    UserCreationForm, but relabels the username field so that the user knows
    they are creating the group superuser.
    """
    def __init__(self, *args, **kwargs):
        super(NewGroupSuperuserForm, self).__init__(*args, **kwargs)
        self.fields['username'].help_text = ''
        self.fields['username'].label = 'Group Superuser Username'
        self.fields['password2'].help_text = ''
        self.fields['password2'].label = 'Password Confirmation'

class NewAPIAccessDataForm(ModelForm):
    """Form for creating a set of access data for the GitHub and Zendesk
    APIs."""
    class Meta:
        model = APIAccessData
        exclude = ('git_token',)
        widgets = {
            'zen_token': PasswordInput()
        }

class ChangeAPIAccessDataForm(ModelForm):
    """Form for changing a set of access data for the GitHub and Zendesk
    APIs. Despite passing this form an instance, it will still not display the
    instance's initial values for the encrypted fields, so it is necessary to
    manually set each field initial value with its cooresponding value in the
    passed instance."""
    class Meta:
        model = APIAccessData
        exclude = ('git_token',)

    def __init__(self, *args, **kwargs):
        super(ChangeAPIAccessDataForm, self).__init__(*args, **kwargs)
        for key, value in self.fields.items():
            self.fields[key].initial = getattr(self.instance, key)

class UserProfileForm(ModelForm):
    """Form to set the two editable fields of a user's profile data."""
    class Meta:
        model = UserProfile
        fields = ('utc_offset', 'view_type')

class ProfileChoiceField(ModelChoiceField):
    """Extends django's normal ModelChoiceField in order to display the
    usernames of each user profile that the user selection forms filter by."""
    def label_from_instance(self, obj):
        return obj.user.username

class ActiveUserSelectionForm(Form):
    """Form for selecting a specific GitZen user's profile. Filters the
    UserProfile list down to just the users in the group that use the passed
    API access model, and then excludes the group superuser and users who are
    set as inactive."""
    def __init__(self, api_access_model, *args, **kwargs):
        super(ActiveUserSelectionForm, self).__init__(*args, **kwargs)
        self.fields['profile'] = \
                ProfileChoiceField(queryset=UserProfile.objects.\
                            filter(api_access_data=api_access_model).\
                            exclude(is_group_superuser=True).\
                            exclude(user__is_active=False),
                            label='Select User')

class InactiveUserSelectionForm(Form):
    """Form for selecting a specific GitZen user's profile. Filters the
    UserProfile list down to just the users in the group that use the passed
    API access model, and then excludes the group superuser and users who are
    set as active."""
    def __init__(self, api_access_model, *args, **kwargs):
        super(InactiveUserSelectionForm, self).__init__(*args, **kwargs)
        self.fields['profile'] = \
                ProfileChoiceField(queryset=UserProfile.objects.\
                            filter(api_access_data=api_access_model).\
                            exclude(is_group_superuser=True).\
                            exclude(user__is_active=True),
                            label='Select User')
