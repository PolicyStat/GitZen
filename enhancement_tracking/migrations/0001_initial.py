# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserProfile'
        db.create_table('enhancement_tracking_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
            ('api_access_model', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['enhancement_tracking.APIAccessData'])),
            ('is_group_superuser', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('utc_offset', self.gf('django.db.models.fields.IntegerField')(default=0, null=True)),
            ('view_type', self.gf('django.db.models.fields.CharField')(default='ZEN', max_length=3)),
        ))
        db.send_create_signal('enhancement_tracking', ['UserProfile'])

        # Adding model 'APIAccessData'
        db.create_table('enhancement_tracking_apiaccessdata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('git_org', self.gf('django.db.models.fields.CharField')(max_length=75)),
            ('git_repo', self.gf('django.db.models.fields.CharField')(max_length=75)),
            ('git_token', self.gf('customfields.EncryptedCharField')(max_length=165)),
            ('zen_name', self.gf('django.db.models.fields.CharField')(max_length=75)),
            ('zen_token', self.gf('customfields.EncryptedCharField')(max_length=165)),
            ('zen_url', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('zen_tags', self.gf('customfields.SeparatedValuesField')()),
            ('zen_schema', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('zen_fieldid', self.gf('django.db.models.fields.IntegerField')(null=True)),
        ))
        db.send_create_signal('enhancement_tracking', ['APIAccessData'])


    def backwards(self, orm):
        # Deleting model 'UserProfile'
        db.delete_table('enhancement_tracking_userprofile')

        # Deleting model 'APIAccessData'
        db.delete_table('enhancement_tracking_apiaccessdata')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'enhancement_tracking.apiaccessdata': {
            'Meta': {'object_name': 'APIAccessData'},
            'git_org': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'git_repo': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'git_token': ('customfields.EncryptedCharField', [], {'max_length': '165'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'zen_fieldid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'zen_name': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'zen_schema': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'zen_tags': ('customfields.SeparatedValuesField', [], {}),
            'zen_token': ('customfields.EncryptedCharField', [], {'max_length': '165'}),
            'zen_url': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'enhancement_tracking.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'api_access_model': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['enhancement_tracking.APIAccessData']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_group_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'utc_offset': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'view_type': ('django.db.models.fields.CharField', [], {'default': "'ZEN'", 'max_length': '3'})
        }
    }

    complete_apps = ['enhancement_tracking']