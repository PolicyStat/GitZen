from django.db import models
from django.contrib.auth.models import User, UserManager

class GZUser(User):
    git_name = models.CharField(max_length=75)
    git_repo = models.CharField(max_length=75)
    git_key = models.CharField(max_length=75)
    zen_name = models.CharField(max_length=75)
    zen_url = models.CharField(max_length=100)
    zen_pass = models.CharField(max_length=75)

    objects = UserManager()
