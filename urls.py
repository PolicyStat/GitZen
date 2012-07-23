from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

# The patterns that call the 'check_authentication_frontend' from views and
# send their actual view function as a kwarg are pages that can only be viewed
# if the user is logged into an authenticated user account. If an AnonymousUser
# tries to access those pages, they will be redirected to the login screen.
urlpatterns = patterns('enhancement_tracking.views',
    url(r'^$', 'user_login_form_handler', name='login'),
    url(r'^create/$', 'user_creation_form_handler', name='user_creation'),
    url(r'^confirm_user_creation/$', 'confirm_user_creation', 
        name='confirm_user_creation'),
    url(r'^confirm_git_oauth/$', 'confirm_git_oauth', name='confirm_git_oauth'),
    url(r'^home/$', 'check_authentication_frontend',
        kwargs={'view_function': 'home'}, name='home'),
    url(r'^change/$', 'check_authentication_frontend',
        kwargs={'view_function': 'change_form_handler'},
        name='change_account_data'),
    url(r'^confirm_changes/$', 'check_authentication_frontend',
        kwargs={'view_function': 'confirm_changes'}, name='confirm_changes')
)
