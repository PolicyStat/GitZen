from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

# URL patterns for all users
urlpatterns = patterns('enhancement_tracking.views',
    url(r'^$', 'user_login_form_handler', name='login'),
    url(r'^logout/$', 'user_logout', name='logout'),
    url(r'^create/$', 'user_creation_form_handler', name='user_creation'),
    url(r'^home/$', 'home', name='home'),
    url(r'^change/$', 'change_form_handler', name='change_account_settings'),
    url(r'^confirm_changes/$', 'confirm_changes', name='confirm_changes'),
    url(r'^confirm_user_creation/$', 'confirm_user_creation',
        name='confirm_user_creation'),
    url(r'^confirm_git_oauth/$', 'confirm_git_oauth',
        name='confirm_git_oauth'),
)

# URL patterns only used by superusers
urlpatterns += patterns('enhancement_tracking.views',
    url(r'^superuser_change/(?P<user_id>\d+)/$',
        'superuser_change_form_handler',
        name='superuser_change_account_settings'),
    url(r'^confirm_superuser_changes/(?P<user_id>\d+)/$',
        'confirm_superuser_changes', name='confirm_superuser_changes'),
    url(r'^confirm_user_deactivation/(?P<user_id>\d+)/$',
        'confirm_user_deactivation', name='confirm_user_deactivation'),
    url(r'^confirm_user_activation/(?P<user_id>\d+)/$',
        'confirm_user_activation', name='confirm_user_activation'),
)
