from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('enhancement_tracking.views',
    url(r'^$', 'user_login_form_handler', name='login'),
    url(r'^create/$', 'user_creation_form_handler', name='user_creation'),
    url(r'^home/$', 'home', name='home'),
    url(r'^change/$', 'change_form_handler', name='change'),
    url(r'^git_confirm/$', 'git_oauth_confirm', name='git_confirm'),
    url(r'^confirm/(?P<con_num>\d+)/$', 'confirm', name='confirm'),
) 
