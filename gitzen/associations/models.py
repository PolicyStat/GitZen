from django.db import models
from django.contrib.auth.models import User, UserManager
from encryption import EncryptedCharField

class GZUser(User):
    git_name = models.CharField(max_length=75)
    git_repo = models.CharField(max_length=75)
    git_key = models.EncryptedCharField(max_length=75)
    zen_name = models.CharField(max_length=75)
    zen_url = models.CharField(max_length=100)
    zen_pass = models.EncryptedCharField(max_length=75)

    objects = UserManager()
