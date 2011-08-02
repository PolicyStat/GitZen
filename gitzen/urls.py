from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('associations.views',
    (r'^$', 'login'),
    (r'^main/$', 'home'),
    (r'^close/$', 'close'),
    (r'^git/(?P<git_num>\d+)/$', 'git'),
    (r'^zen/t(?P<zen_num>\d+)/$', 'zenT'),
    (r'^zen/u(?P<user_num>\d+)/$', 'zenU'),
) 
