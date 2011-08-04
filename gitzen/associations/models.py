from django.db import models
from django.contrib.auth.models import User, UserManager
from encryption import EncryptedCharField

class GZUser(User):
    git_name = models.CharField(max_length=75)
    git_repo = models.CharField(max_length=75)
<<<<<<< HEAD
    git_key = EncryptedCharField(max_length=75)
    zen_name = models.CharField(max_length=75)
    zen_url = models.CharField(max_length=100)
    zen_pass = EncryptedCharField(max_length=75)
=======
    git_key = models.EncryptedCharField(max_length=75)
    zen_name = models.CharField(max_length=75)
    zen_url = models.CharField(max_length=100)
    zen_pass = models.EncryptedCharField(max_length=75)
>>>>>>> 8c79ec174176a156ae022a4d313ffb6d117a757d

    objects = UserManager()
