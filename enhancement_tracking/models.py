from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from encryption import EncryptedCharField

class GZUserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    git_name = models.CharField(max_length=30,
                                verbose_name='GitHub Username')
    git_pass = EncryptedCharField(max_length=75,
                                  verbose_name='GitHub Password')
    git_org = models.CharField(max_length=75, 
                               verbose_name='GitHub Organization')
    git_repo = models.CharField(max_length=75,
                                verbose_name='GitHub Repository')
    zen_name = models.CharField(max_length=75,
                                verbose_name='Zendesk User Email')
    zen_token = EncryptedCharField(max_length=75,
                                   verbose_name='Zendesk API Token')
    zen_url = models.CharField(max_length=100,
                               verbose_name='Zendesk URL')
    zen_fieldid = models.IntegerField(null=True,
                                      verbose_name='Zendesk Ticket \
                                      Association Field ID')
    age_limit = models.IntegerField(null=True,
                                    verbose_name='Age Limit (in days) for \
                                    the Tickets')

    def __str__(self):
        return "%s's profile" % self.user
