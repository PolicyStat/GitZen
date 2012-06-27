from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('enhancement_tracking.views',
    url(r'^$', 'user_login', name='login'),
    url(r'^home/$', 'home', name='home'),
    url(r'^change/$', 'change', name='change'),
    url(r'^git-confirm/$', 'git_confirm', name='git-confirm')
    url(r'^confirm/(?P<con_num>\d+)/$', 'confirm', name='confirm'),
) 
