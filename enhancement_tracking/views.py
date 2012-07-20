from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.urlresolvers import reverse
import requests
from requests.exceptions import RequestException
from requests_oauth2 import OAuth2
from datetime import datetime, timedelta
from time import mktime
from settings import CLIENT_ID, CLIENT_SECRET
from enhancement_tracking.forms import UserForm, UserProfileForm, \
                                        ProfileChangeForm, \
                                        ZendeskTokenChangeForm

# Constant URL string for accessing the GitHub API. It requires a GitHub
# organization/user, repository, and issue number for the string's formatting.
GIT_ISSUE_URL = 'https://api.github.com/repos/%(organization)s/' \
                '%(repository)s/issues/%(issue_number)i'

# Constant OAuth handler and authorization URL for access to GitHub's OAuth.
OAUTH2_HANDLER = OAuth2(CLIENT_ID, CLIENT_SECRET, site='https://github.com/',
                        redirect_uri='http://gitzen.herokuapp.com/git_confirm',
                        authorization_url='login/oauth/authorize',
                        token_url='login/oauth/access_token')
GIT_AUTH_URL = OAUTH2_HANDLER.authorize_url('repo')

# Constant URL string for searching for tickets through the Zendesk API. It
# requires the custom URL subdomain of the specific company whose information
# is being accessed for the string's formatting.
ZEN_SEARCH_URL = '%(subdomain)s/api/v2/search.json'

# Constant search query used to access open Zendesk problem and incident tickets
# form its API.
ZEN_TICKET_SEARCH_QUERY = 'type:ticket ticket_type:incident ' \
                        'ticket_type:problem status:open'

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

def user_creation_form_handler(request):
    """Process the requests from the User Creation page.
    
    If any of the fields in the submitted form are not completed properly, the
    User Creation page will come up again with those fields marked as needing to
    be properly filled.

    Parameters:
        request - The request object that contains the form data submitted from
                    the User Creation page.
    """
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            
            # Store the profile in the session so the GitHub access token
            # can be added to it through OAuth on the next pages.
            request.session['profile'] = profile
            return HttpResponseRedirect(reverse('confirm', args=[1]))
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    return render_to_response('user_creation.html', {'user_form': user_form,
                              'profile_form': profile_form}, 
                              context_instance=RequestContext(request))
            
def change_form_handler(request):
    """Processes the requests from the Change Account Data page. This includes
    requests from the password change form, profile change form, and Zendesk API
    token chnage form.

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
                return HttpResponseRedirect(reverse('confirm', args=[2]))
            profile_change_form = ProfileChangeForm()
            zen_token_change_form = ZendeskTokenChangeForm()

        # Process profile change form
        elif 'profile_input' in request.POST:
            profile_change_form = ProfileChangeForm(data=request.POST,
                                                    instance=profile)
            if profile_change_form.is_valid():
                profile_change_form.save()
                return HttpResponseRedirect(reverse('confirm', args=[2]))
            password_change_form = PasswordChangeForm(user=request.user)
            zen_token_change_form = ZendeskTokenChangeForm()
        
        # Process Zendesk API Token change form
        elif 'zen_token_input' in request.POST: 
            zen_token_change_form = ZendeskTokenChangeForm(data=request.POST,
                                                           instance=profile)
            if zen_token_change_form.is_valid():
                zen_token_change_form.save()
                return HttpResponseRedirect(reverse('confirm', args=[2]))
            password_change_form = PasswordChangeForm(user=request.user)
            profile_change_form = ProfileChangeForm()
    else:
        password_change_form = PasswordChangeForm(user=request.user)
        profile_change_form = ProfileChangeForm(instance=profile)
        zen_token_change_form = ZendeskTokenChangeForm()
    
    return render_to_response('change.html', 
                              {'password_change_form': password_change_form, 
                               'profile_change_form': profile_change_form,
                               'zen_token_change_form': zen_token_change_form,
                               'auth_url': GIT_AUTH_URL},
                              context_instance=RequestContext(request))

def confirm(request, con_num):
    """Renders the confirmation page to confirm the successful submission of
    data from the different forms.

    Parameters:
        request - The request object sent with the call to render the page.
        con_num - The number to identify which confirmation message should be
                    displayed on the page.
    """
    return render_to_response('confirm.html',
                              {'con_num': con_num, 'auth_url': GIT_AUTH_URL},
                              context_instance=RequestContext(request))

def git_oauth_confirm(request):
    """Finishes the OAuth2 access web flow after the user goes to the
    GIT_AUTH_URL in either the user login or change forms. Adds the access token
    to the user profile. For a newly created user, their profile was added to
    the session when the user was created. This data is deleted from the
    session afterwards.

    Parameters:
        request - The request object that should contain the returned code from
                    GitHub in its GET parameters in addition to the user profile
                    that the access token should be added to.
    """
    if 'profile' in request.session: # Authorizing for a new user
        profile = request.session['profile']
        new_user = True
    else: # Changing Authorization for an existing user
        profile = request.user.get_profile()
        new_user = False

    if 'error' in request.GET:
        profile.git_token = ''
        access = False
    else:
        code = request.GET['code']
        response = OAUTH2_HANDLER.get_token(code)
        profile.git_token = response['access_token'][0]
        access = True
    
    profile.save()
    if new_user:
        del request.session['profile']

    return render_to_response('git_confirm.html', 
                              {'access': access, 'new_user': new_user},
                              context_instance=RequestContext(request))

def home(request):
    """Gathers and builds the enhancement tracking data and renders the home
    page of the app with this data.
    
    Parameters:
        request - The request object that contains the current user's data.
    """
    profile = request.user.get_profile() # Current user profile
    zen_fieldid = profile.zen_fieldid # The field ID for the custom field on
                                      # Zendesk tickets that contains their 
                                      # associated GitHub issue number.
    utc_offset = profile.utc_offset # The UTC offset for the current user's time
                                    # zone.
    render_data = {} # Data to be rendered to the home page

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
        render_data['error_message'] = 'There was an error connecting to the \
                %s API: %s. Try adjusting your account settings.' % (e.args[1],
                                                                     e.args[0])
        return render_to_response('home.html', render_data,
                                    context_instance=RequestContext(request))
        
    render_data = build_enhancement_data(zen_tickets, zen_user_reference,
                                         git_tickets, zen_fieldid, utc_offset)

    # Add additional data to be rendered to the home page
    render_data['api_requests_successful'] = True
    render_data['zen_url'] = profile.zen_url
    
    return render_to_response('home.html', render_data,
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
    except RequestException as e:
        e.args = (e.args[0], 'Zendesk')
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
    except RequestException as e:
        e.args = (e.args[0], 'Zendesk')
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
    except RequestException as e:
        e.args = (e.args[0], 'GitHub')
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
                                        ticket in GitHub.
        'broken_enhancements' - List of Zendesk tickets that have improper data
                                    in their GitHub issue association field.
                                    This could be the result of a typo or some
                                    other user error.
    """
    tracking = [] # Enhancements whose Zendesk and GitHub tickets are both open.
    need_attention = [] # Enhancements with either a closed Zendesk ticket or
                        # a closed GitHub ticket. Because one of these tickets
                        # is closed, the other needs attention.
    unassociated_enhancements = [] # Requested enhancements from Zendesk 
                                   # tickets that have no associatied GitHub
                                   # ticket assigned to them.
    broken_enhancements = [] # Requested enhancements from Zendesk with a broken
                             # GitHub issue association field.

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
        
        # Check if it has no associated GitHub ticket
        if association_data is None or association_data.split('-')[0] != 'gh':
            unassociated_enhancements.append(enhancement_data)
        
        else:
            # Add GitHub data to enhancement data object
            git_issue = {}
            for issue in git_tickets:
                if issue['number'] == int(association_data.split('-')[1]):
                    git_issue = issue
                    break
            # Check if it has a broken GitHub association field
            if not git_issue:
                enhancement_data['broken_assoc'] = association_number
                broken_enhancements.append(enhancement_data)
                continue
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
    """
    broken_test = {
        'zen_id': '9001',
        'zen_subject': "Test. It's over 9000!",
        'zen_requester': 'Nick McLaughlin',
        'zen_date': '09/09/09',
        'zen_time': '11:11 PM',
        'broken_assoc': 'gh-1337'
    }
    broken_enhancements.append(broken_test)
    """

    built_data = {
        'tracking': tracking,
        'need_attention': need_attention,
        'unassociated_enhancements': unassociated_enhancements,
        'broken_enhancements': broken_enhancements,
    }

    return built_data
