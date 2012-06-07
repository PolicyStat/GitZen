from django.db import models
from django.contrib.auth.models import User, UserManager
from encryption import EncryptedCharField

class GZUser(User):
    git_name = models.CharField(max_length=75)
    git_pass = EncryptedCharField(max_length=75)
    git_org = models.CharField(max_length=75)
    git_repo = models.CharField(max_length=75)
    zen_name = models.CharField(max_length=75)
    zen_pass = EncryptedCharField(max_length=75)
    zen_url = models.CharField(max_length=100)
    zen_viewid = models.CharField(max_length=25)
    zen_fieldid = models.CharField(max_length=50)

    objects = UserManager()
