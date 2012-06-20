from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('associations.views',
    url(r'^$', 'user_login', name='login'),
    url(r'^home/$', 'home', name='home'),
    url(r'^change/$', 'change', name='change'),
    url(r'^nope/(?P<nope_num>\d+)/$', 'nope', name='nope'),
    url(r'^confirm/(?P<con_num>\d+)/$', 'confirm', name='confirm'),
) 
