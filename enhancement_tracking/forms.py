from django.forms import Form, CharField, IntegerField, PasswordInput

class LogForm(Form):
    """Form for login of an existing user."""
    
    username = CharField(max_length=30)
    password = CharField(max_length=75, widget=PasswordInput)

class UserForm(ModelForm):
    """User form for creating a new user."""
    class Meta:
        model = User
        fields = ['username', 'password']

class UserProfileForm(ModelForm):
    """User profile form for creating a new user."""
    class Meta:
        model = GZUserProfile

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
