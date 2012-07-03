from django.db import models
from django.contrib.auth.models import User
from encryption import EncryptedCharField

class GZUserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    git_token = EncryptedCharField(max_length=75)
    git_org = models.CharField(max_length=75, 
                               verbose_name='GitHub Organization')
    git_repo = models.CharField(max_length=75,
                                verbose_name='GitHub Repository')
    zen_name = models.CharField(max_length=75,
                                verbose_name='Zendesk User Email')
    zen_token = EncryptedCharField(max_length=75,
                                   verbose_name='Zendesk API Token')
    zen_url = models.CharField(max_length=100,
                               verbose_name='Zendesk URL Subdomain')
    zen_fieldid = models.IntegerField(null=True,
                                      verbose_name='Zendesk Ticket \
                                      Association Field ID')

    def __str__(self):
        return "%s's profile" % self.user
