#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    m_file, m_pathname, m_description = imp.find_module('settings', ['gitzen'])
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

settings = imp.load_module('settings', m_file, m_pathname, m_description)

if __name__ == "__main__":
    execute_manager(settings)
