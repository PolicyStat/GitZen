from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from encryption import EncryptedCharField

class GZUserProfile(models.Model):
    user = models.OneToOneField(User)
    git_name = models.CharField(max_length=75, label='GitHub Username')
    git_pass = EncryptedCharField(max_length=75, label='GitHub Password')
    git_org = models.CharField(max_length=75, label='GitHub Organization')
    git_repo = models.CharField(max_length=75, label='GitHub Repository')
    zen_name = models.CharField(max_length=75, label='Zendesk User Email')
    zen_token = EncryptedCharField(max_length=75, label='Zendesk API Token')
    zen_url = models.CharField(max_length=100, label='Zendesk URL')
    zen_fieldid = models.IntegerField(null=True, label='Zendesk Ticket \
                                      Association Field ID')
    age_limit = models.IntegerField(null=True, label='Age Limit (in days) for \
                                    the Tickets')

    def __str__(self):
        return "%s's profile" % self.user

def create_user_profile(sender, instance, created, **kwargs):
    if created:
        GZUser.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)
