from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.core.cache import cache
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordChangeForm, SetPasswordForm
)
from django.core.urlresolvers import reverse
from requests.exceptions import RequestException
from requests_oauth2 import OAuth2
from datetime import datetime, timedelta
from time import mktime
from itertools import chain
from settings import CLIENT_ID, CLIENT_SECRET
from enhancement_tracking.models import UserProfile
from enhancement_tracking.cache_actions import (
    build_cache_index, update_cache_index
)
from enhancement_tracking.forms import (
    NewUserForm, NewGroupSuperuserForm, NewAPIAccessDataForm,
    ChangeAPIAccessDataForm, UserProfileForm, ActiveUserSelectionForm,
    InactiveUserSelectionForm
)

# Constant OAuth handler and authorization URL for access to GitHub's OAuth.
OAUTH2_HANDLER = OAuth2(CLIENT_ID, CLIENT_SECRET, site='https://github.com/',
                        redirect_uri='http://gitzen.herokuapp.com/' \
                                     'confirm_git_oauth',
                        authorization_url='login/oauth/authorize',
                        token_url='login/oauth/access_token')
GIT_AUTH_URL = OAUTH2_HANDLER.authorize_url('repo')

def user_login_form_handler(request):
    """Processes the requests from the login page and authenticates the login of
    an existing user.

    Parameters:
        request - The request object that contains the POST data from the login
                    forms.
    """ 
    if request.method == 'POST':
        log_form = AuthenticationForm(data=request.POST)
        if log_form.is_valid():
            login(request, log_form.get_user())
            return HttpResponseRedirect(reverse('home'))
    else:
        log_form = AuthenticationForm()

    return render_to_response('login.html', {'log_form': log_form}, 
                              context_instance=RequestContext(request))

def group_creation_form_handler(request):
    """Process the requests from the User Group Creation page.
    
    Parameters:
        request - The request object that contains the form data submitted from
                    the User Group Creation page.
    """
    if request.method == 'POST':
        group_superuser_form = NewGroupSuperuserForm(data=request.POST)
        api_access_data_form = NewAPIAccessDataForm(data=request.POST)
        if group_superuser_form.is_valid() and api_access_data_form.is_valid():
            group_superuser = group_superuser_form.save()
            api_access_data = api_access_data_form.save()
            group_superuser_profile = \
                    UserProfile(user=group_superuser,
                                api_access_data=api_access_data,
                                is_group_superuser=True)
            group_superuser_profile.save()

            # Authenticate and login the newly created group superuser so a
            # GitHub access token can be added to the group's API access model
            # through OAuth on the next pages.
            user = authenticate(
                username=group_superuser_form.cleaned_data['username'],
                password=group_superuser_form.cleaned_data['password1']
            )
            login(request, user)
            return HttpResponseRedirect(reverse('confirm_group_creation'))
    else:
        group_superuser_form = NewGroupSuperuserForm()
        api_access_data_form = NewAPIAccessDataForm()

    return render_to_response('group_creation.html',
                              {'group_superuser_form': group_superuser_form,
                              'api_access_data_form': api_access_data_form}, 
                              context_instance=RequestContext(request))

@login_required
def change_form_handler(request):
    """Processes the requests from the Change Account Data page. This includes
    requests from the password change form and profile change form.

    Parameters:
        request - The request object that contains the POST data from one of the
                    change forms.
    """
    profile = request.user.get_profile()

    if request.POST:
        # Process password change form
        if 'password_input' in request.POST:
            password_change_form = PasswordChangeForm(user=request.user,
                                                      data=request.POST)
            if password_change_form.is_valid():
                password_change_form.save()
                return HttpResponseRedirect(reverse('confirm_changes'))
            profile_change_form = SecuredProfileChangeForm(instance=profile)

        # Process profile change form
        elif 'profile_input' in request.POST:
            profile_change_form = UserProfileForm(data=request.POST,
                                                  instance=profile)
            if profile_change_form.is_valid():
                profile_change_form.save()
                return HttpResponseRedirect(reverse('confirm_changes'))
            password_change_form = PasswordChangeForm(user=request.user)
        
        else:
            return HttpResponseRedirect(reverse('change_account_settings'))

    else:
        password_change_form = PasswordChangeForm(user=request.user)
        profile_change_form = UserProfileForm(instance=profile)
    
    return render_to_response('change_account_settings.html', 
                              {'password_change_form': password_change_form, 
                               'profile_change_form': profile_change_form},
                              context_instance=RequestContext(request))

@login_required
@user_passes_test(lambda user: user.get_profile().is_group_superuser)
def superuser_change_form_handler(request, user_id):
    """Process the requests from the group superuser Change Account Settings
    page for the user selected on the superuser home page. This includes
    requests from the profile change form and the set password form.

    Parameters:
        request - The request object that contains the POST data from the froms.
        user_id - The ID number of the user that should be represented and
                    modified by the change forms.
    """
    changing_user = User.objects.get(id=user_id)
    changing_profile = changing_user.get_profile()

    if request.POST:
        # Process profile change form
        if 'profile_input' in request.POST:
            profile_change_form = UserProfileForm(data=request.POST,
                                                  instance=changing_profile)
            if profile_change_form.is_valid():
                profile_change_form.save()
                return HttpResponseRedirect(
                    reverse('confirm_superuser_changes',
                            kwargs={'user_id': user_id})
                )
            set_password_form = SetPasswordForm(user=changing_user)
        
        # Process password change form
        elif 'password_input' in request.POST:
            set_password_form = SetPasswordForm(user=changing_user,
                                                data=request.POST)
            if set_password_form.is_valid():
                set_password_form.save()
                return HttpResponseRedirect(
                    reverse('confirm_superuser_changes',
                            kwargs={'user_id': user_id})
                )
            profile_change_form = FullProfileChangeForm(
                                    instance=changing_profile)
 
        else:
            return HttpResponseRedirect(
                reverse('superuser_change_account_settings',
                        kwargs={'user_id': user_id})
            )

    else:
        set_password_form = SetPasswordForm(user=changing_user)
        profile_change_form = UserProfileForm(instance=changing_profile)
    
    return render_to_response('superuser_change_account_settings.html', 
                              {'username': changing_user.username,
                               'set_password_form': set_password_form, 
                               'profile_change_form': profile_change_form,
                               'auth_url': GIT_AUTH_URL},
                              context_instance=RequestContext(request))

@login_required
def user_logout(request):
    """Logs out the currently logged in user.

    Parameters:
        request - The request object that contains the information for the user
                    that is being logged out.
    """
    logout(request)
    return HttpResponseRedirect(reverse('login'))

@login_required
def confirm_changes(request):
    """Renders the confirmation page to confirm the successful changes made to
    the current user's account settings.

    Parameters:
        request - The request object sent with the call to the confirm page if
                    the requested changes were successfully made to the user's
                    account.
    """
    return render_to_response('confirm_changes.html',
                              context_instance=RequestContext(request))

@login_required
@user_passes_test(lambda user: user.get_profile().is_group_superuser)
def confirm_superuser_changes(request, user_id):
    """Renders the confirmation page to confirm the successful changes made to
    the selected user's account settings by the group superuser.

    Parameters:
        request - The request object sent with the call to the confirm page if
                    the requested changes were successfully made to the selected
                    user's account.
        user_id - The ID of the user that was just modified.
    """
    username = User.objects.get(id=user_id).username
    return render_to_response('confirm_superuser_changes.html',
                              {'username': username},
                              context_instance=RequestContext(request))

@login_required
@user_passes_test(lambda user: user.get_profile().is_group_superuser)
def confirm_group_creation(request):
    """Renders the confirmation page to confirm the successful creation of a new
    user group.

    Parameters:
        request - The request object sent with the call to the confirm page if a
                    group and group superuser were successfully created from the
                    group creation page.
    """
    return render_to_response('confirm_group_creation.html',
                              {'auth_url': GIT_AUTH_URL},
                              context_instance=RequestContext(request))

@login_required
@user_passes_test(lambda user: user.get_profile().is_group_superuser)
def confirm_git_oauth(request):
    """Finishes the OAuth2 access web flow after the user goes to the
    GIT_AUTH_URL in either the group creation or change forms. Adds the access
    token to the API access model for the group. For a newly created group,
    their API access model was added to the session when the group was created.
    This data is deleted from the session afterwards.

    Parameters:
        request - The request object that should contain the returned code from
                    GitHub in its GET parameters in addition to the API access
                    model that the access token should be added to.
    """
    api_access_data = request.user.get_profile().api_access_data
    
    """
    if 'error' in request.GET:
        api_access_data.git_token = ''
        access_granted = False
    else:
        code = request.GET['code']
        response = OAUTH2_HANDLER.get_token(code)
        api_access_data.git_token = response['access_token'][0]
        access_granted = True
    api_access_data.save()
    """
    api_access_data.git_token = '147a87738db7ac19c865845e19652b8134ad0099'
    api_access_data.save()
    access_granted = True
    product_name = api_access_data.product_name
    return render_to_response('confirm_git_oauth.html', 
                              {'access_granted': access_granted,
                               'product_name': product_name},
                              context_instance=RequestContext(request))

@login_required
@user_passes_test(lambda user: user.get_profile().is_group_superuser)
def confirm_cache_building(request, is_reset):
    """Calls the function to build and index the cache for the API access model
    of the logged in group superuser and renders a page that tells if the
    caching was successful or not.

    Parameters:
        request - The request object that should have a group superuser logged
                    into it.
    """
    context = {
        'is_reset': is_reset,
        'product_name': request.user.get_profile().api_access_data.product_name
    }

    try:
        build_cache_index(request.user.get_profile().api_access_data)
    except RequestException as e:
        context['caching_successful'] = False
        context['error_message'] = "There was an error connecting to the " \
                "%(API_name)s API: %(exception_message)s. Try adjusting the" \
                " group's API access settings." % \
                {'API_name': e.args[1], 'exception_message': e.args[0]}
        return render_to_response('confirm_cache_building.html', context,
                                  context_instance=RequestContext(request))
    
    context['caching_successful'] = True
    return render_to_response('confirm_cache_building.html', context,
                              context_instance=RequestContext(request))

@login_required
@user_passes_test(lambda user: user.get_profile().is_group_superuser)
def confirm_user_creation(request, user_id):
    """Renders the confirmation page to confirm the successful creation of a new
    user.

    Parameters:
        request - The request object sent with the call to the confirm page if
                    the user was created successfully.
        user_id - The ID of the user that was just created.
    """
    user = User.objects.get(id=user_id)
    username = user.username
    product_name = user.get_profile().api_access_data.product_name
    return render_to_response('confirm_user_creation.html',
                              {'username': username,
                               'product_name': product_name},
                              context_instance=RequestContext(request))

@login_required
@user_passes_test(lambda user: user.get_profile().is_group_superuser)
def confirm_user_deactivation(request, user_id):
    """Renders the confirmation page to confirm the successful deactivation of a
    user by the superuser.

    Parameters:
        request - The request object sent with the call to the confirm page if
                    the selected user was successfully deactivated.
        user_id - The ID of the user that was just deactivated by the superuser.
        """
    deactivated_username = User.objects.get(id=user_id).username
    return render_to_response('confirm_user_deactivation.html',
                              {'deactivated_username': deactivated_username},
                              context_instance=RequestContext(request))

@login_required
@user_passes_test(lambda user: user.get_profile().is_group_superuser)
def confirm_user_activation(request, user_id):
    """Renders the confirmation page to confirm the successful activation of a
    previously deactivated user by the superuser.

    Parameters:
        request - The request object sent with the call to the confirm page if
                    the selected user was successfully activated.
        user_id - The ID of the user that just activated by the superuser.
    """
    activated_username = User.objects.get(id=user_id).username
    return render_to_response('confirm_user_activation.html',
                              {'activated_username': activated_username},
                              context_instance=RequestContext(request))

@login_required
@user_passes_test(lambda user: user.get_profile().is_group_superuser)
def confirm_api_access_changes(request):
    """Renders the confirmation page to confirm the successful changes made to
    the API access settings for the superuser's group.

    Parameters:
        request - The request object sent with the call to the confirm page if
                    the requested changes were successfully made to the API
                    access settings.
    """
    product_name = request.user.get_profile().api_access_data.product_name
    return render_to_response('confirm_api_access_changes.html',
                              {'product_name': product_name},
                              context_instance=RequestContext(request))

@login_required
def home(request):
    """Gathers and builds the enhancement tracking data and renders the home
    page of the app with this data. If the request for the page is from a
    group superuser, it gets redirected to the group_superuser_home function.
    
    Parameters:
        request - The request object that contains the current user's data.
    """
    # If the user is a group superuser, render the group superuser home page
    # that allows for group superuser actions instead of the regular user home
    # page.
    if request.user.get_profile().is_group_superuser:
        return group_superuser_home(request)

    profile = request.user.get_profile() # Current user's profile
    utc_offset = profile.utc_offset
    api_access_data = profile.api_access_data
    product_name = api_access_data.product_name
    context = {}
    
    try:
        update_cache_index(api_access_data)
    except RequestException as e:
        context['api_requests_successful'] = False
        context['error_message'] = 'There was an error connecting to ' \
                'the %(API_name)s API: %(exception_message)s. If the error ' \
                'persists after refreshing the page, inform the superuser ' \
                'for %(product_name)s that the API access settings may need ' \
                'adjustment.' % {'API_name': e.args[1],
                                 'exception_message': e.args[0],
                                 'product_name': product_name}
        return render_to_response('home.html', context,
                                    context_instance=RequestContext(request))
    
    # Account for the time zone offset and get the enhancement data
    cache_data = cache.get(api_access_data.id)
    enhancement_tables = _time_adjust_enhancement_data(cache_data, utc_offset)
    context = enhancement_tables
        
    # Add additional data to be used in the context of the home page
    context['api_requests_successful'] = True
    context['product_name'] = product_name
    context['zen_url'] = api_access_data.zen_url
    if profile.view_type == 'ZEN':
        context['is_zendesk_user'] = True
    else:
        context['is_zendesk_user'] = False
    context['is_github_user'] = not context['is_zendesk_user']
    
    return render_to_response('home.html', context,
                              context_instance=RequestContext(request))

def _time_adjust_enhancement_data(cache_data, utc_offset):
    """Adjusts the enhancement data from the cache so that all of the dates and
    times are in the passed UTC time zone.

    Parameters:
        cache_data - A dictionary of enhancement data stored under a group index
                        in the cache.
        utc_offset - The numeric UTC offset for the time zone that the
                        enhancement data should be converted to.

    Returns the four enhancement tables (need_attention, tracking,
    unassociated_enhancements, and not_git_enhancements) adjusted to the passed
    time zone in a dictionary with the keys being the tables' names.
    """
    offset_delta = timedelta(hours=utc_offset)

    for enhancement in chain(cache_data['need_attention'],
                             cache_data['tracking']):
        zen_datetime = enhancement['zen_datetime'] + offset_delta
        enhancement['zen_date'] = zen_datetime.strftime('%m/%d/%Y')
        enhancement['zen_time'] = zen_datetime.strftime('%I:%M %p')
        enhancement['zen_sortable_datetime'] = \
                mktime(zen_datetime.timetuple())
        git_datetime = enhancement['git_datetime'] + offset_delta
        enhancement['git_date'] = git_datetime.strftime('%m/%d/%Y')
        enhancement['git_time'] = git_datetime.strftime('%I:%M %p')
        enhancement['git_sortable_datetime'] = \
                mktime(git_datetime.timetuple())

    for enhancement in chain(cache_data['unassociated_enhancements'],
                             cache_data['not_git_enhancements']):
        zen_datetime = enhancement['zen_datetime'] + offset_delta
        enhancement['zen_date'] = zen_datetime.strftime('%m/%d/%Y')
        enhancement['zen_time'] = zen_datetime.strftime('%I:%M %p')
        enhancement['zen_sortable_datetime'] = \
                mktime(zen_datetime.timetuple())

    enhancement_tables = {
        'need_attention': cache_data['need_attention'],
        'tracking': cache_data['tracking'],
        'unassociated_enhancements': cache_data['unassociated_enhancements'],
        'not_git_enhancements': cache_data['not_git_enhancements']
    }

    return enhancement_tables

@login_required
@user_passes_test(lambda user: user.get_profile().is_group_superuser)
def group_superuser_home(request):
    """Processes the various form requests from the group superuser home page.
    This includes the forms to create a new user, to deactivate or reactivate a
    user, to change the group API access settings, and to change the password
    for the superuser.

    Parameters:
        request - The request object that contains the group superuser data and
                    the POST data from the various forms.
    """
    api_access_data = request.user.get_profile().api_access_data
    product_name = api_access_data.product_name

    if request.POST:
        # Process the new user form for getting the information needed to create
        # a new user and add them to the group
        if 'user_creation_input' in request.POST:
            new_user_form = NewUserForm(data=request.POST)
            user_profile_form = UserProfileForm(data=request.POST)
            if new_user_form.is_valid() and user_profile_form.is_valid():
                user = new_user_form.save()
                user_profile = user_profile_form.save(commit=False)
                user_profile.user = user
                user_profile.api_access_data = api_access_data
                user_profile.save()

                return HttpResponseRedirect(
                    reverse('confirm_user_creation', 
                            kwargs={'user_id': user.id})
                )
            user_select_form = ActiveUserSelectionForm(api_access_data)
            user_deactivate_form = ActiveUserSelectionForm(api_access_data)
            user_activate_form = InactiveUserSelectionForm(api_access_data)
            api_access_change_form = \
                    ChangeAPIAccessDataForm(instance=api_access_data)
            password_change_form = PasswordChangeForm(user=request.user)

        # Process the user selection form for selecting a user to modify
        elif 'user_select_input' in request.POST:
            user_select_form = ActiveUserSelectionForm(api_access_data,
                                                       data=request.POST)
            if user_select_form.is_valid():
                user = user_select_form.cleaned_data['profile'].user
                return HttpResponseRedirect(
                    reverse('superuser_change_account_settings',
                            kwargs={'user_id': user.id})
                )
            new_user_form = NewUserForm()
            user_profile_form = UserProfileForm()
            user_deactivate_form = ActiveUserSelectionForm(api_access_data)
            user_activate_form = InactiveUserSelectionForm(api_access_data)
            api_access_change_form = \
                    ChangeAPIAccessDataForm(instance=api_access_data)
            password_change_form = PasswordChangeForm(user=request.user)

        # Process the user selection form for deactivating a user
        elif 'user_deactivate_input' in request.POST:
            user_deactivate_form = ActiveUserSelectionForm(api_access_data,
                                                           data=request.POST)
            if user_deactivate_form.is_valid():
                user = user_deactivate_form.cleaned_data['profile'].user
                user.is_active = False
                user.save()

                return HttpResponseRedirect(
                    reverse('confirm_user_deactivation',
                            kwargs={'user_id': user.id})
                )
            new_user_form = NewUserForm()
            user_profile_form = UserProfileForm()
            user_select_form = ActiveUserSelectionForm(api_access_data)
            user_activate_form = InactiveUserSelectionForm(api_access_data)
            api_access_change_form = \
                    ChangeAPIAccessDataForm(instance=api_access_data)
            password_change_form = PasswordChangeForm(user=request.user)
        
        # Process the user selection form for activating a user
        elif 'user_activate_input' in request.POST:
            user_activate_form = InactiveUserSelectionForm(api_access_data,
                                                           data=request.POST)
            if user_activate_form.is_valid():
                user = user_activate_form.cleaned_data['profile'].user
                user.is_active = True
                user.save()
                
                return HttpResponseRedirect(
                    reverse('confirm_user_activation',
                            kwargs={'user_id': user.id})
                )
            new_user_form = NewUserForm()
            user_profile_form = UserProfileForm()
            user_select_form = ActiveUserSelectionForm(api_access_data)
            user_deactivate_form = ActiveUserSelectionForm(api_access_data)
            api_access_change_form = \
                    ChangeAPIAccessDataForm(instance=api_access_data)
            password_change_form = PasswordChangeForm(user=request.user)

        # Process the API access data form for changing the API access data for
        # the group.
        elif 'api_access_change_input' in request.POST:
            api_access_change_form = ChangeAPIAccessDataForm(data=request.POST,
                                                      instance=api_access_data)
            if api_access_change_form.is_valid():
                api_access_change_form.save()
                return HttpResponseRedirect(
                    reverse('confirm_api_access_changes')
                )
            new_user_form = NewUserForm()
            user_profile_form = UserProfileForm()
            user_select_form = ActiveUserSelectionForm(api_access_data)
            user_deactivate_form = ActiveUserSelectionForm(api_access_data)
            user_activate_form = InactiveUserSelectionForm(api_access_data)
            password_change_form = PasswordChangeForm(user=request.user)

        # Process superuser password change form
        elif 'password_change_input' in request.POST:
            password_change_form = PasswordChangeForm(user=request.user,
                                                      data=request.POST)
            if password_change_form.is_valid():
                password_change_form.save()
                return HttpResponseRedirect(reverse('confirm_changes'))
            new_user_form = NewUserForm()
            user_profile_form = UserProfileForm()
            user_select_form = ActiveUserSelectionForm(api_access_data)
            user_deactivate_form = ActiveUserSelectionForm(api_access_data)
            user_activate_form = InactiveUserSelectionForm(api_access_data)
            api_access_change_form = \
                    ChangeAPIAccessDataForm(instance=api_access_data)

        else:
            return HttpResponseRedirect(reverse('home'))
    
    else:
        new_user_form = NewUserForm()
        user_profile_form = UserProfileForm()
        user_select_form = ActiveUserSelectionForm(api_access_data)
        user_deactivate_form = ActiveUserSelectionForm(api_access_data)
        user_activate_form = InactiveUserSelectionForm(api_access_data)
        api_access_change_form = \
                ChangeAPIAccessDataForm(instance=api_access_data)
        password_change_form = PasswordChangeForm(user=request.user)

    context = {
        'new_user_form': new_user_form,
        'user_profile_form': user_profile_form,
        'user_select_form': user_select_form,
        'user_deactivate_form': user_deactivate_form,
        'user_activate_form': user_activate_form,
        'api_access_change_form': api_access_change_form,
        'password_change_form': password_change_form,
        'product_name': product_name,
        'auth_url': GIT_AUTH_URL
    }

    return render_to_response('superuser_home.html', context,
                              context_instance=RequestContext(request))
