from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('associations.views',
    (r'^as/$', 'home'),
    (r'^as/close/$', 'close'),
    (r'^as/git/(?P<git_num>\d+)/$', 'git'),
    (r'^as/zen/t(?P<zen_num>\d+)/$', 'zenT'),
    (r'^as/zen/u(?P<user_num>\d+)/$', 'zenU'),
) 
