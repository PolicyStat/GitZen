from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('associations.views',
    (r'^$', 'user_login'),
    (r'^main/$', 'home'),
    (r'^change/$', 'change'),
    (r'^close/$', 'close'),
    (r'^nope/(?P<nope_num>\d+)/$', 'nope'),
    (r'^confirm/(?P<con_num>\d+)/$', 'confirm'),
    (r'^git/(?P<git_num>\d+)/$', 'git'),
    (r'^zen/t(?P<zen_num>\d+)/$', 'zenT'),
    (r'^zen/u(?P<user_num>\d+)/$', 'zenU'),
) 
