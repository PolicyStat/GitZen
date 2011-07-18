from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^as/$', 'associations.views.home'),
    (r'^as/new/$', 'associations.views.new'),
    (r'^as/git/(?P<git_num>\d+)/$', 'associations.views.git'),
    (r'^as/zen/(?P<zen_num>\d+)/$', 'associations.views.zen'),
) 
