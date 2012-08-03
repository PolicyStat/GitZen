from django.db import models
from django.contrib.auth.models import User
from customfields import EncryptedCharField, SeparatedValuesField

VIEW_TYPE_CHOICES = (
    ('GIT', 'GitHub'),
    ('ZEN', 'Zendesk')
)

class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    api_access_model = models.ForeignKey('APIAccessData')
    is_group_superuser = models.BooleanField(default=False)
    utc_offset = models.IntegerField(null=True, default=0, 
                                     verbose_name='Time Zone (UTC Offset)')
    view_type = models.CharField(max_length=3, choices=VIEW_TYPE_CHOICES,
                                 default='ZEN', verbose_name='View Type')

    def __str__(self):
        return "%s's profile" % self.user

class APIAccessData(models.Model):
    git_org = models.CharField(max_length=75, 
                               verbose_name='GitHub Organization')
    git_repo = models.CharField(max_length=75,
                                verbose_name='GitHub Repository')
    git_token = EncryptedCharField(max_length=75)
    zen_name = models.CharField(max_length=75,
                                verbose_name='Zendesk User Email')
    zen_token = EncryptedCharField(max_length=75,
                                   verbose_name='Zendesk API Token')
    zen_url = models.CharField(max_length=100,
                               verbose_name='Zendesk URL Subdomain')
    zen_tags = SeparatedValuesField(verbose_name='Zendesk Tags to Filter By')
    zen_schema = models.CharField(max_length=25,
                                  verbose_name='Zendesk External ' \
                                  'Association Naming Schema')
    zen_fieldid = models.IntegerField(null=True,
                                      verbose_name='Zendesk Ticket ' \
                                      'Association Field ID')
