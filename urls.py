from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('associations.views',
    (r'^$', 'user_login'),
    (r'^home/$', 'home'),
    (r'^change/$', 'change'),
    (r'^nope/(?P<nope_num>\d+)/$', 'nope'),
    (r'^confirm/(?P<con_num>\d+)/$', 'confirm'),
) 
