import binascii
import random
import string
import Crypto.Cipher
 
from django import forms
from django.db import models
from django.conf import settings
from south.modelsinspector import add_introspection_rules
 
class BaseEncryptedField(models.Field):
 
    def __init__(self, *args, **kwargs):
        cipher = kwargs.pop('cipher', 'AES')
        imp = __import__('Crypto.Cipher', globals(), locals(), [cipher], -1)
        self.cipher = getattr(imp, cipher).new(settings.SECRET_KEY[:32])
        self.prefix = '$%s$' % cipher
 
        max_length = kwargs.get('max_length', 40)
        mod = max_length % self.cipher.block_size
        if mod > 0:
            max_length += self.cipher.block_size - mod
        kwargs['max_length'] = max_length * 2 + len(self.prefix)
 
        models.Field.__init__(self, *args, **kwargs)
 
    def _is_encrypted(self, value):
        return isinstance(value, basestring) and value.startswith(self.prefix)
 
    def _get_padding(self, value):
        mod = len(value) % self.cipher.block_size
        if mod > 0:
            return self.cipher.block_size - mod
        return 0
 
 
    def to_python(self, value):
        if self._is_encrypted(value):
            return self.cipher.decrypt(binascii.a2b_hex(value \
                            [len(self.prefix):])).split('\0')[0]
        return value
 
    def get_db_prep_value(self, value, connection, prepared):
        if value is not None and not self._is_encrypted(value):
            padding = self._get_padding(value)
            if padding > 0:
                value += "\0" + ''.join([random.choice(string.printable) for \
                                        index in range(padding-1)])
            value = self.prefix + binascii.b2a_hex(self.cipher.encrypt(value))
        return value 

class EncryptedCharField(BaseEncryptedField):
    __metaclass__ = models.SubfieldBase
 
    def get_internal_type(self):
        return "CharField"
 
    def formfield(self, **kwargs):
        defaults = {'max_length': self.max_length}
        defaults.update(kwargs)
        return super(EncryptedCharField, self).formfield(**defaults)

add_introspection_rules([], ["^customfields\.BaseEncryptedField"])
add_introspection_rules([], ["^customfields\.EncryptedCharField"])

class SeparatedValuesField(models.TextField):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        self.token = kwargs.pop('token', ',')
        super(SeparatedValuesField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not value: return
        if isinstance(value, list):
            return value
        return value.split(self.token)

    def get_db_prep_value(self, value):
        if not value: return
        assert(isinstance(value, list) or isinstance(value, tuple))
        return self.token.join([unicode(s) for s in value])

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

add_introspection_rules([], ["^customfields\.SeperatedValuesField"])
