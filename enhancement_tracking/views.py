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
import requests
from requests.exceptions import RequestException
from requests_oauth2 import OAuth2
from datetime import datetime, timedelta
from time import mktime
from settings import CLIENT_ID, CLIENT_SECRET
from enhancement_tracking.forms import (
    UserForm, GroupSuperuserForm, APIAccessDataForm, UserProfileChangeForm,
    ActiveUserSelectionForm, InactiveUserSelectionForm
)

# Constant URL string for accessing the GitHub API. It requires a GitHub
# organization/user, repository, and issue number for the string's formatting.
GIT_ISSUE_URL = 'https://api.github.com/repos/%(organization)s/' \
                '%(repository)s/issues/%(issue_number)i'

# Constant OAuth handler and authorization URL for access to GitHub's OAuth.
OAUTH2_HANDLER = OAuth2(CLIENT_ID, CLIENT_SECRET, site='https://github.com/',
                        redirect_uri='http://gitzen.herokuapp.com/' \
                                     'confirm_git_oauth',
                        authorization_url='login/oauth/authorize',
                        token_url='login/oauth/access_token')
GIT_AUTH_URL = OAUTH2_HANDLER.authorize_url('repo')

# Constant URL string for searching for tickets through the Zendesk API. It
# requires the custom URL subdomain of the specific company whose information
# is being accessed for the string's formatting.
ZEN_SEARCH_URL = '%(subdomain)s/api/v2/search.json'

# Constant search query used to access open Zendesk problem and incident tickets
# form its API.
ZEN_TICKET_SEARCH_QUERY = 'type:ticket tags:product_enhancement status:open'

# Constant URL string for accessing Zendesk users through the Zendesk API. It
# requires the custom URL subdomain for the specific company whose users are
# being accessed and the ID number of the user being accessed for the string's
# formatting.
ZEN_USER_URL = '%(subdomain)s/api/v2/users/%(user_id)i.json'

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
        group_superuser_form = GroupSuperuserForm(data=request.POST)
        api_access_data_form = APIAccessDataForm(data=request.POST)
        if group_superuser_form.is_valid() and api_access_data_form.is_valid():
            group_superuser = group_superuser_form.save()
            api_access_model = api_access_data_form.save()
            group_superuser_profile = \
                    UserProfile(user=group_superuser,
                                api_access_model=api_access_model,
                                is_group_superuser=True)
            group_superuser_profile.save()

            # Store the API access model in the session so the GitHub access
            # token can be added to it through OAuth on the next pages.
            request.session['new_api_access_model'] = api_access_model
            return HttpResponseRedirect(reverse('confirm_group_creation'))
    else:
        group_superuser_form = GroupSuperuserForm()
        api_access_data_form = APIAcessDataForm()

    return render_to_response('group_creation.html',
                              {'group_superuser_form': group_superuser_form,
                              'api_access_data_form': api_access_data_form}, 
                              context_instance=RequestContext(request))

@login_required
def change_form_handler(request):
    """Processes the requests from the Change Account Data page. This includes
    requests from the password change form, profile change form, and Zendesk API
    token change form.

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
            zen_token_change_form = ZendeskTokenChangeForm()

        # Process profile change form
        elif 'profile_input' in request.POST:
            profile_change_form = SecuredProfileChangeForm(data=request.POST,
                                                           instance=profile)
            if profile_change_form.is_valid():
                profile_change_form.save()
                return HttpResponseRedirect(reverse('confirm_changes'))
            password_change_form = PasswordChangeForm(user=request.user)
            zen_token_change_form = ZendeskTokenChangeForm()
        
        # Process Zendesk API Token change form
        elif 'zen_token_input' in request.POST: 
            zen_token_change_form = ZendeskTokenChangeForm(data=request.POST,
                                                           instance=profile)
            if zen_token_change_form.is_valid():
                zen_token_change_form.save()
                return HttpResponseRedirect(reverse('confirm_changes'))
            password_change_form = PasswordChangeForm(user=request.user)
            profile_change_form = SecuredProfileChangeForm(instance=profile)
        
        else:
            return HttpResponseRedirect(reverse('change_account_settings'))
    else:
        password_change_form = PasswordChangeForm(user=request.user)
        profile_change_form = SecuredProfileChangeForm(instance=profile)
        zen_token_change_form = ZendeskTokenChangeForm()
    
    return render_to_response('change_account_settings.html', 
                              {'password_change_form': password_change_form, 
                               'profile_change_form': profile_change_form,
                               'zen_token_change_form': zen_token_change_form,
                               'auth_url': GIT_AUTH_URL},
                              context_instance=RequestContext(request))

@login_required
@user_passes_test(lambda u: u.is_superuser)
def superuser_change_form_handler(request, user_id):
    """Process the requests from the superuser Change Account Data page for the
    user selected on the superuser home page. This includes requests from the
    profile change form and the set password form.

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
            profile_change_form = FullProfileChangeForm(data=request.POST,
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
            return HttpResponseRedirect(reverse('change_account_settings'))

    else:
        set_password_form = SetPasswordForm(user=changing_user)
        profile_change_form = FullProfileChangeForm(instance=changing_profile)
    
    return render_to_response('superuser_change_account_settings.html', 
                              {'username': changing_user.username,
                               'set_password_form': set_password_form, 
                               'profile_change_form': profile_change_form,
                               'auth_url': GIT_AUTH_URL},
                              context_instance=RequestContext(request))

def user_logout(request):
    """Logs out the currently logged in user.

    Parameters:
        request - The request object that contains the information for the user
                    that is being logged out.
    """
    logout(request)
    return HttpResponseRedirect(reverse('login'))

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
    if 'new_api_access_model' in request.session: # Authorizing for a new group
        api_access_model = request.session['new_api_access_model']
        is_new_group = True
    else: # Changing Authorization for an existing group
        api_access_model = request.user.get_profile().api_access_model
        is_new_group = False

    if 'error' in request.GET:
        api_access_model.git_token = ''
        access_granted = False
    else:
        code = request.GET['code']
        response = OAUTH2_HANDLER.get_token(code)
        api_access_model.git_token = response['access_token'][0]
        access_granted = True
    
    api_access_model.save()
    if is_new_group:
        del request.session['new_api_access_model']

    return render_to_response('confirm_git_oauth.html', 
                              {'access_granted': access_granted,
                               'is_new_group': is_new_group},
                              context_instance=RequestContext(request))

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
def confirm_superuser_changes(request, user_id):
    """Renders the confirmation page to confirm the successful changes made to
    the selected user's account settings by the superuser.

    Parameters:
        request - The request object sent with the call to the confirm page if
                    the requested changes were successfully made to the selected
                    user's account.
        user_id - The ID of the user that was just modified by the superuser.
    """
    username = User.objects.get(id=user_id).username
    return render_to_response('confirm_superuser_changes.html',
                              {'username': username},
                              context_instance=RequestContext(request))

@login_required
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
def home(request):
    """Gathers and builds the enhancement tracking data and renders the home
    page of the app with this data. If the request for the page is from a
    superuser, it gets redirected to the superuser_home function.
    
    Parameters:
        request - The request object that contains the current user's data.
    """
    # If the user is a superuser, render the superuser home page that allows for
    # the editing of user account settings instead of the regular user home
    # page.
    if request.user.is_superuser:
        return superuser_home(request)

    profile = request.user.get_profile() # Current user profile
    zen_fieldid = profile.zen_fieldid # The field ID for the custom field on
                                      # Zendesk tickets that contains their 
                                      # associated GitHub issue number.
    utc_offset = profile.utc_offset # The UTC offset for the current user's time
                                    # zone.
    context = {} # Data to be used in the context of the home page

    zen_tickets = [] # List of the open problem or incident tickets in Zendesk.
    zen_user_reference = {} # Dictionary reference of the user IDs and 
                            # user names associated with the Zendesk tickets in
                            # zen_tickets.
    git_tickets = [] # List of the GitHub tickets associated with the Zendesk
                     # tickets in zen_tickets.
    
    try:
        zen_tickets = get_zen_tickets(profile)
        zen_user_ids, git_issue_numbers = get_id_lists(zen_tickets, zen_fieldid)
        zen_user_reference = get_zen_users(profile, zen_user_ids)
        git_tickets = get_git_tickets(profile, git_issue_numbers)
    except RequestException as e:
        render_data['api_requests_successful'] = False
        render_data['error_message'] = 'There was an error connecting to ' \
                'the %(API_name)s API: %(exception_message)s. Try adjusting ' \
                'your account settings.' % {'API_name': e.args[1],
                                            'exception_message': e.args[0]}
        return render_to_response('home.html', render_data,
                                    context_instance=RequestContext(request))
        
    context = build_enhancement_data(zen_tickets, zen_user_reference,
                                     git_tickets, zen_fieldid, utc_offset)

    # Add additional data to be used in the context of the home page
    context['api_requests_successful'] = True
    context['zen_url'] = profile.zen_url
    if profile.view_type == 'ZEN':
        context['is_zendesk_user'] = True
    else:
        context['is_zendesk_user'] = False
    context['is_github_user'] = not context['is_zendesk_user']
    
    return render_to_response('home.html', context,
                              context_instance=RequestContext(request))

@login_required
@user_passes_test(lambda u: u.is_superuser)
def superuser_home(request):
    """Processes the various form requests from the superuser home page. This
    includes the forms to select a user to change their account, to select a
    user to delete their account, and to change the password for the superuser.

    Parameters:
        request - The request object that contains the superuser data and the
                    POST data from the various forms.
    """
    if request.POST:
        # Process the user selection form for changing a user
        if 'user_change_input' in request.POST:
            user_change_form = ActiveUserSelectionForm(data=request.POST)
            if user_change_form.is_valid():
                user = user_change_form.cleaned_data['user']
                return HttpResponseRedirect(
                    reverse('superuser_change_account_settings',
                            kwargs={'user_id': user.id})
                )
            user_deactivate_form = ActiveUserSelectionForm()
            user_activate_form = InactiveUserSelectionForm()
            password_change_form = PasswordChangeForm(user=request.user)

        # Process the user selection form for deactivating a user
        elif 'user_deactivate_input' in request.POST:
            user_delete_form = ActiveUserSelectionForm(data=request.POST)
            if user_delete_form.is_valid():
                user = user_delete_form.cleaned_data['user']
                user.is_active = False
                user.save()

                return HttpResponseRedirect(
                    reverse('confirm_user_deactivation',
                            kwargs={'user_id': user.id})
                )
            user_change_form = ActiveUserSelectionForm()
            user_activate_form = InactiveUserSelectionForm()
            password_change_form = PasswordChangeForm(user=request.user)
        
        # Process the user selection form for activating a user
        elif 'user_activate_input' in request.POST:
            user_activate_form = InactiveUserSelectionForm(data=request.POST)
            if user_activate_form.is_valid():
                user = user_activate_form.cleaned_data['user']
                user.is_active = True
                user.save()
                
                return HttpResponseRedirect(
                    reverse('confirm_user_activation',
                            kwargs={'user_id': user.id})
                )
            user_change_form = ActiveUserSelectionForm()
            user_deactivate_form = ActiveUserSelectionForm()
            password_change_form = PasswordChangeForm(user=request.user)

        # Process superuser password change form
        elif 'password_change_input' in request.POST:
            password_change_form = PasswordChangeForm(user=request.user,
                                                      data=request.POST)
            if password_change_form.is_valid():
                password_change_form.save()
                return HttpResponseRedirect(reverse('confirm_changes'))
            user_change_form = ActiveUserSelectionForm()
            user_deactivate_form = ActiveUserSelectionForm()
            user_activate_form = InactiveUserSelectionForm()

        else:
            return HttpResponseRedirect(reverse('home'))
    
    else:
        user_change_form = ActiveUserSelectionForm()
        user_deactivate_form = ActiveUserSelectionForm()
        user_activate_form = InactiveUserSelectionForm()
        password_change_form = PasswordChangeForm(user=request.user)

    return render_to_response('superuser_home.html',
                              {'user_change_form': user_change_form,
                               'user_deactivate_form': user_deactivate_form,
                               'user_activate_form': user_activate_form,
                               'password_change_form': password_change_form},
                              context_instance=RequestContext(request))

def get_zen_tickets(profile):
    """Gets all of the open problem and incident Zendesk tickets using the
    Zendesk API.

    Parameters:
        profile - The profile object that contains the current user's data 
                    necessary to access the tickets on their Zendesk account.

    Returns a gathered list of Zendesk tickets.
    """
    zen_name_tk = profile.zen_name + '/token' # Zendesk user email set up for 
                                              # API token authorization.
    zen_tickets = []
    page = 1
    
    try:
        while True:
            request_zen_tickets = requests.get(ZEN_SEARCH_URL % \
                                               {'subdomain': profile.zen_url}, 
                                    params={'query': ZEN_TICKET_SEARCH_QUERY,
                                            'sort_by': 'updated_at',
                                            'sort_order': 'desc',
                                            'per_page': 100,
                                            'page': page},
                                    auth=(zen_name_tk, profile.zen_token))
            if request_zen_tickets.status_code != 200:
                request_zen_tickets.raise_for_status()
            zen_tickets.extend(request_zen_tickets.json['results'])
            if request_zen_tickets.json['next_page'] is not None:
                page += 1
            else:
                break

    # Catches exceptions from requests.get() or raise_for_status()
    except RequestException as e:
        # Redefines the args attribute of the exception to contain both the
        # original error message and the name of the API responsible for causing
        # the exception.
        e.args = (e.args[0], 'Zendesk')

        # Raise the exception so it can be caught by the except in the home
        # function for further processing.
        raise

    return zen_tickets

def get_id_lists(zen_tickets, zen_fieldid):
    """Gets lists of the Zendesk user IDs and the GitHub issue numbers that are
    associated with the passed list of Zendesk tickets.

    Parameters:
        zen_tickets - A list of Zendesk tickets whose associated GitHub issue
                    numbers and Zendesk user IDs are desired.
        zen_fieldid - The ID number of the custom field in Zendesk tickets that
                        holds its associated GitHub issue number.

    Returns a tuple of two value with the first being the gathered list of
    associated Zendesk user IDs and with the second being the gathered list
    of associated GitHub issue numbers.
    """
    
    # Get Zendesk user IDs that are associated with Zendesk tickets.
    zen_user_ids = []
    for ticket in zen_tickets:
        zen_user_ids.append(ticket['requester_id'])
    zen_user_ids = set(zen_user_ids) # Remove duplicates
    
    # Get GitHub issue numbers that are associated with the Zendesk tickets.
    git_issue_numbers = []
    for ticket in zen_tickets:
        association_data = ''
        for field in ticket['fields']:
            if field['id'] == zen_fieldid:
                if field['value'] is not None:
                    association_data = field['value'].split('-')
                break
        if association_data and association_data[0] == 'gh':
            git_issue_numbers.append(int(association_data[1]))
    git_issue_numbers = set(git_issue_numbers) # Remove duplicates

    return (zen_user_ids, git_issue_numbers)

def get_zen_users(profile, zen_user_ids):
    """Gets the full Zendesk user records for each user ID number in the passed
    list.

    Parameters:
        profile - The profile object that contains the current user's data
                    necessary to access the users on their Zendesk account.  
        zen_user_ids - A list of Zendesk user IDs whose full user records are 
                        desired.

    Returns a dictionary reference table with Zendesk user ID numbers as keys
    and their cooresponding user names as values.
    """
    zen_name_tk = profile.zen_name + '/token' # Zendesk user email set up for 
                                              # API token authorization.
    zen_user_reference = {} # Dictionary that allows the look up of Zendesk user
                            # names by their ID number.
    try:
        for id_number in zen_user_ids:
            request_zen_user = requests.get(ZEN_USER_URL % \
                                            {'subdomain': profile.zen_url,
                                             'user_id': id_number},
                                    auth=(zen_name_tk, profile.zen_token))
            if request_zen_user.status_code != 200:
                request_zen_user.raise_for_status()
            zen_user_reference[id_number] = \
                    request_zen_user.json['user']['name']

   # Catches exceptions from requests.get() or raise_for_status()
    except RequestException as e:
        # Redefine the args attribute of the exception to contain both the
        # original error message and the name of the API responsible for causing
        # the exception.
        e.args = (e.args[0], 'Zendesk')

        # Raise the exception so it can be caught by the except in the home
        # function for further processing.
        raise
    
    return zen_user_reference

def get_git_tickets(profile, git_issue_numbers):
    """Gets the full GitHub ticket records for each issue number in the passed
    list.

    Parameters:
        profile - The profile object that contains the current user's data
                    necessary to access the tickets on their GitHub account.  
        git_issue_numbers - A list of GitHub issue numbers whose full ticket
                                records are desired.

    Returns a list with a GitHub ticket record for each of the issue numbers
    passed to the function.
    """
    git_tickets = []
    
    try:
        for number in git_issue_numbers:
            request_git_tickets = requests.get(GIT_ISSUE_URL % \
                                               {'organization': profile.git_org,
                                                'repository': profile.git_repo,
                                                'issue_number': number}, 
                                               params={'access_token':
                                                       profile.git_token}
                                              )
            if request_git_tickets.status_code != 200:
                request_git_tickets.raise_for_status()
            git_tickets.append(request_git_tickets.json)

    # Catches exceptions from requests.get() or raise_for_status()
    except RequestException as e:
        # Redefine the args attribute of the exception to contain both the
        # original error message and the name of the API responsible for causing
        # the exception.
        e.args = (e.args[0], 'GitHub')

        # Raise the exception so it can be caught by the except in the home
        # function for further processing.
        raise

    return git_tickets

def build_enhancement_data(zen_tickets, zen_user_reference, git_tickets,
                           zen_fieldid, utc_offset):
    """Builds the enhancement tracking tables from the Zendesk and GitHub data.
    
    Parameters:
        zen_tickets - A list of open Zendesk tickets to build the enhancement
                        data from.
        zen_user_reference - A dictionary reference that can be used to look up
                                Zendesk user names by their ID number.
        git_tickets - A list of GitHub tickets that cooresponds with the
                        associated GitHub issue numbers of the Zendesk tickets
                        in zen_tics.
        zen_fieldid - The ID number of the custom field that holds the ticket
                        association value for a given Zendesk ticket.
        utc_offset - The UTC offset for the current user's time zone. Used to
                        format the date and time values for each ticket to the
                        current user's time zone.

    Returns a dictionary of the built data with the following keys and values:
        'tracking' - List of enhancements in the process of being worked on.
        'need_attention' - List of enhancements where one half of the
                            enhancement is completed, but the other is not.
        'unassociated_enhancements' - List of Zendesk tickets requesting an 
                                        enhancement that have no associated
                                        external ticket.
        'not_git_enhancements' - List of Zendesk tickets that have an associated
                                    external ticket, but the ticket is not
                                    labeled as being part of GitHub. (i.e. The
                                    association string is not in the format
                                    "gh-###").
    """
    tracking = [] # Enhancements whose Zendesk and GitHub tickets are both open.
    need_attention = [] # Enhancements with either a closed Zendesk ticket or
                        # a closed GitHub ticket. Because one of these tickets
                        # is closed, the other needs attention.
    unassociated_enhancements = [] # Requested enhancements from Zendesk 
                                   # tickets that have no associated external
                                   # ticket assigned to them.
    not_git_enhancements = [] # Requested enhancements from Zendesk that have an
                              # associated external ticket, but the ticket is
                              # not labeled as being part of GitHub.

    # Iterate through the Zendesk tickets using their data to classify them
    # as being tracked, needing attention, broken, or not being tracked.
    for ticket in zen_tickets:

        # Add Zendesk data to enhancement data object
        association_data = ''
        for field in ticket['fields']:
            if field['id'] == zen_fieldid:
                association_data = field['value']
                break
        enhancement_data = {} # Enhancement data object
        enhancement_data['zen_id'] = ticket['id']
        enhancement_data['zen_requester'] = \
                zen_user_reference[ticket['requester_id']]
        enhancement_data['zen_subject'] = ticket['subject']
        zen_datetime = datetime.strptime(ticket['updated_at'],
                                       "%Y-%m-%dT%H:%M:%SZ")
        zen_datetime = zen_datetime + timedelta(hours=utc_offset)
        enhancement_data['zen_date'] = zen_datetime.strftime('%m/%d/%Y')
        enhancement_data['zen_time'] = zen_datetime.strftime('%I:%M %p')
        enhancement_data['zen_sortable_datetime'] = \
                mktime(zen_datetime.timetuple())
        
        # Check if the enhancement has no associated ticket
        if not association_data:
            unassociated_enhancements.append(enhancement_data)

        # Check if the enhancement's associated ticket is not a GitHub ticket
        split_association_data = association_data.split('-')
        elif len(split_association_data) != 2 or \
                split_association_data[0] != 'gh' or \
                not split_association_data[1].isdigit():
            enhancement_data['non_git_association'] = association_data
            not_git_enhancements.append(enhancement_data)
        
        # Add GitHub data to the enhancement data object
        else:
            git_issue = {}
            for issue in git_tickets:
                if issue['number'] == int(split_association_data[1]):
                    git_issue = issue
                    break
            enhancement_data['git_id'] = git_issue['number']
            enhancement_data['git_url'] = git_issue['html_url']
            enhancement_data['git_status'] = git_issue['state']
            git_datetime = datetime.strptime(git_issue['updated_at'],
                                             "%Y-%m-%dT%H:%M:%SZ")
            git_datetime = git_datetime + timedelta(hours=utc_offset)
            enhancement_data['git_date'] = git_datetime.strftime('%m/%d/%Y')
            enhancement_data['git_time'] = git_datetime.strftime('%I:%M %p')
            enhancement_data['git_sortable_datetime'] = \
                    mktime(git_datetime.timetuple())
            
            # Check if the enhacement should be tracked (Both tickets are
            # open).
            if enhancement_data['git_status'] == 'open':
                tracking.append(enhancement_data)
            
            # Check if the enhancement is in need of attention (The GitHub
            # ticket is closed).
            else:
                need_attention.append(enhancement_data)

    built_data = {
        'tracking': tracking,
        'need_attention': need_attention,
        'unassociated_enhancements': unassociated_enhancements,
        'not_git_enhancements': not_git_enhancements,
    }

    return built_data
