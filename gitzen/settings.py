# Django settings for gitzen project.

import os

# Environment variables are Strings, not booleans
DEBUG = False
env_debug = os.environ.get('GITZEN_DEBUG', 'False')
if not env_debug == 'False':
    DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

from memcacheify import memcacheify

CACHES = memcacheify()

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# The relative URL of the login page for the application.
LOGIN_URL = '/'

# The absolute URL of the website for the application.
ABSOLUTE_SITE_URL = os.environ.get(
    'GITZEN_ABSOLUTE_SITE_URL', 'http://gitzen.policystat.com')

# The default email address to use when sending out emails from GitZen.
DEFAULT_FROM_EMAIL = os.environ.get(
    'GITZEN_DEFAULT_FROM_EMAIL', 'development@policystat.com')

# The following five constants are used to access a SMTP host to send out emails
# for GitZen.
EMAIL_HOST = os.environ.get(
    'GITZEN_EMAIL_HOST', 'email-smtp.us-east-1.amazonaws.com')

EMAIL_PORT = os.environ.get('GITZEN_EMAIL_PORT', 25)

EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.environ.get('GITZEN_SMTP_USER', '')

EMAIL_HOST_PASSWORD = os.environ.get('GITZEN_SMTP_PASSWORD', '')

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.environ.get('GITZEN_MEDIA_ROOT', '')
if not MEDIA_ROOT:
    MEDIA_ROOT = os.path.abspath(
        os.path.join(PROJECT_ROOT, '..', 'upload'))

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_ROOT = os.environ.get('GITZEN_MEDIA_URL', '')
if not MEDIA_ROOT:
    MEDIA_URL = ABSOLUTE_SITE_URL + '/upload/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.environ.get('GITZEN_STATIC_ROOT', '')
if not STATIC_ROOT:
    STATIC_ROOT = os.path.abspath(
        os.path.join(PROJECT_ROOT, '..', 'static'))

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = os.environ.get('GITZEN_STATIC_URL', '')
if not STATIC_URL:
    STATIC_URL = ABSOLUTE_SITE_URL + '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = STATIC_URL + 'static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'media'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = os.environ['GITZEN_DJANGO_SECRET_KEY']

# Consumer key for OAuth access of the GitHub API
CLIENT_ID = os.environ['GITZEN_GITHUB_CLIENT_ID']

# Consumer secret for OAuth access of the GitHub API
CLIENT_SECRET = os.environ['GITZEN_GITHUB_CLIENT_SECRET']

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.gzip.GZipMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'gitzen.enhancement_tracking',
    'south'
)

AUTH_PROFILE_MODULE = 'gitzen.enhancement_tracking.UserProfile'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# Grab the JUSTONEDB_DBI_URL and use it for the DATABASE_URL if it exists
justonedb_dbi_url = os.environ.get('JUSTONEDB_DBI_URL', None)
if justonedb_dbi_url:
    os.environ['DATABASE_URL'] = justonedb_dbi_url

# Allow an environment DATABASE_URL for configuration
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(default='postgres://localhost')
}

# If you'd like to override any settings for local development, put them in a
# settings_local.py in the same directory as settings.py
try:
    import settings_local
    for k, v in settings_local.__dict__.items():
        if not k.startswith('__'):
            globals()[k] = v
except ImportError:
    pass
