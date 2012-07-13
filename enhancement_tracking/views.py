from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.urlresolvers import reverse
from enhancement_tracking.forms import UserForm, UserProfileForm, \
                                        ProfileChangeForm
from settings import CLIENT_ID, CLIENT_SECRET
import requests
from requests.exceptions import RequestException
from requests_oauth2 import OAuth2
from datetime import datetime, timedelta

# Constant URL string for accessing the GitHub API. The first %s is the
# organization/user name, the second %s is the repository name, and the thrid %s
# is the issue number of the ticket being accessed.
GIT_ISSUE_URL = 'https://api.github.com/repos/%s/%s/issues/%s'

# Constant OAuth handler and authorization URL for access to GitHub's OAuth.
OAUTH2_HANDLER = OAuth2(CLIENT_ID, CLIENT_SECRET, site='https://github.com/',
                        redirect_uri='http://gitzen.herokuapp.com/git_confirm',
                        authorization_url='login/oauth/authorize',
                        token_url='login/oauth/access_token')
GIT_AUTH_URL = OAUTH2_HANDLER.authorize_url('repo')

# Constant URL string for searching for tickets through the Zendesk API. The %s
# is the custom URL subdomain for the specific company whose tickets are being
# accessed.
ZEN_SEARCH_URL = '%s/api/v2/search.json'

# Constant search query used to access open Zendesk problem and incident tickets
# form its API.
ZEN_TICKET_SEARCH_QUERY = 'type:ticket ticket_type:incident \
                            ticket_type:problem status:open'

# Constant URL string for accessing Zendesk users through the Zendesk API. The
# first %s if the custom URL subdomain for the specific company whose users are
# being accessed, and the second %s is the ID number of the user being accessed.
ZEN_USER_URL = '%s/api/v2/users/%s.json'

def user_login(request):
    """Processes the requests from the login page. 
    
    Authenticates the login of an existing user or creates a new user by adding
    their user data to the database. If any of the fields in the submitted form
    are not completed properly, the login page will come up again with those
    fields marked as needing to be properly filled.

    Parameters:
        request - The request object that contains the POST data from the login
                    forms.
    """

    if request.method == 'POST':
        if 'log' in request.POST:  # Process login form
            logform = AuthenticationForm(data=request.POST)
            if logform.is_valid():
                login(request, logform.get_user())
                return HttpResponseRedirect(reverse('home'))
            uform = UserForm()
            pform = UserProfileForm()

        elif 'new' in request.POST:  # Process new user form
            uform = UserForm(data=request.POST)
            pform = UserProfileForm(data=request.POST)
            if uform.is_valid() and pform.is_valid():
                user = uform.save()
                profile = pform.save(commit=False)
                profile.user = user
                profile.save()
                
                # Store the profile in the session so the GitHub access token
                # can be added to it through OAuth on the next pages.
                request.session['profile'] = profile
                return HttpResponseRedirect(reverse('confirm', args=[1]))
            logform = AuthenticationForm()
    else:
        logform = AuthenticationForm()
        uform = UserForm()
        pform = UserProfileForm()

    return render_to_response('login.html', {'logform': logform,
                                'uform': uform, 'pform': pform}, 
                              context_instance=RequestContext(request))

def change(request):
    """Processes the requests from the Change Account Data page.

    All of the fields on the change forms are optional so that the user can
    change only the account data that they want changed.

    Parameters:
        request - The request object that contains the POST data from the change
                    form.
    """

    if request.method == 'POST':
        if 'password' in request.POST: # Process password change form
            pwform = PasswordChangeForm(user=request.user, data=request.POST)
            if pwform.is_valid():
                pwform.save()
                return HttpResponseRedirect(reverse('confirm', args=[2]))
            prform = ProfileChangeForm()
        
        elif 'profile' in request.POST: # Process profile change form
            prform = ProfileChangeForm(data=request.POST,
                                       instance=request.user.get_profile())
            if prform.is_valid():
                prform.save()
                return HttpResponseRedirect(reverse('confirm', args=[2]))
            pwform = PasswordChangeForm(user=request.user)
    else:
        pwform = PasswordChangeForm(user=request.user)
        prform = ProfileChangeForm()
    
    return render_to_response('change.html', 
                              {'pwform': pwform, 'prform': prform,
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
        new_auth = True
    else: # Changing Authorization for an existing user
        profile = request.user.get_profile()
        new_auth = False

    if 'error' in request.GET:
        profile.git_token = ''
        access = False
    else:
        code = request.GET['code']
        response = OAUTH2_HANDLER.get_token(code)
        profile.git_token = response['access_token'][0]
        access = True
    
    profile.save()
    if new_auth:
        del request.session['profile']

    return render_to_response('git_confirm.html', 
                              {'access': access, 'new_auth': new_auth},
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
        zen_tickets = get_zen_tickets(request)
        zen_user_ids, git_issue_numbers = get_id_lists(zen_tickets, zen_fieldid)
        zen_user_reference = get_zen_users(request, zen_user_ids)
        git_tickets = get_git_tickets(request, git_issue_numbers)
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

def get_zen_tickets(request):
    """Gets all of the open problem and incident Zendesk tickets using the
    Zendesk API.

    Parameters:
        request - The request object that contains the current user's data 
                    necessary to access the tickets on their Zendesk account.

    Returns a gathered list of Zendesk tickets.
    """
    profile = request.user.get_profile()
    zen_name_tk = profile.zen_name + '/token' # Zendesk user email set up for 
                                              # API token authorization.
    zen_tickets = []
    page = 1
    
    try:
        while True:
            request_zen_tickets = requests.get(ZEN_SEARCH_URL %
                                               profile.zen_url, 
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
    zen_user_ids = list(set(zen_user_ids)) # Remove duplicates
    
    # Get GitHub issue numbers that are associated with the Zendesk tickets.
    git_issue_numbers = []
    for ticket in zen_tickets:
        association_data = []
        for field in ticket['fields']:
            if field['id'] == zen_fieldid:
                if field['value'] is not None:
                    association_data = field['value'].split('-')
                break
        if association_data and association_data[0] == 'gh':
            git_issue_numbers.append(int(association_data[1]))
    git_issue_numbers = list(set(git_issue_numbers)) # Remove duplicates

    return (zen_user_ids, git_issue_numbers)

def get_zen_users(request, zen_user_ids):
    """Gets the full Zendesk user records for each user ID number in the passed
    list.

    Parameters:
        request - The request object that contains the current user's data
                    necessary to access the users on their Zendesk account.  
        zen_user_ids - A list of Zendesk user IDs whose full user records are 
                        desired.

    Returns a dictionary reference table with Zendesk user ID numbers as keys
    and their cooresponding user names as values.
    """
    profile = request.user.get_profile()
    zen_name_tk = profile.zen_name + '/token' # Zendesk user email set up for 
                                              # API token authorization.
    zen_user_reference = {} # Dictionary that allows the look up of Zendesk user
                            # names by their ID number.
    try:
        for id_number in zen_user_ids:
            request_zen_user = requests.get(ZEN_USER_URL % 
                                            (profile.zen_url, id_number),
                                auth=(zen_name_tk, profile.zen_token))
            if request_zen_user.status_code != 200:
                request_zen_user.raise_for_status()
            zen_user_reference[id_number] = \
                    request_zen_user.json['user']['name']
    except RequestException as e:
        e.args = (e.args[0], 'Zendesk')
        raise
    
    return zen_user_reference

def get_git_tickets(request, git_issue_numbers):
    """Gets the full GitHub ticket records for each issue number in the passed
    list.

    Parameters:
        request - The request object that contains the current user's data
                    necessary to access the tickets on their GitHub account.  
        git_issue_numbers - A list of GitHub issue numbers whose full ticket
                                records are desired.

    Returns a list with a GitHub ticket record for each of the issue numbers
    passed to the function.
    """
    profile = request.user.get_profile()
    git_tickets = []
    
    try:
        for number in git_issue_numbers:
            request_git_tickets = requests.get(GIT_ISSUE_URL % \
                                               (profile.git_org,
                                               profile.git_repo, number), 
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
        'broken_enhancements' - List of Zendesk tickets that have improper data
                                    in their GitHub issue association field.
                                    This could be the result of a typo or some
                                    other user error.
        'unassociated_enhancements' - List of Zendesk tickets requesting an 
                                        enhancement that have no associated
                                        ticket in GitHub.
    """
    tracking = [] # Enhancements whose Zendesk and GitHub tickets are both open.
    need_attention = [] # Enhancements with either a closed Zendesk ticket or
                        # a closed GitHub ticket. Because one of these tickets
                        # is closed, the other needs attention.
    broken_enhancements = [] # Requested enhancements from Zendesk with a broken
                             # GitHub issue association field.
    unassociated_enhancements = [] # Requested enhancements from Zendesk 
                                   # tickets that have no associatied GitHub
                                   # ticket assigned to them.

    # Iterate through the Zendesk tickets using their data to classify them
    # as being tracked, needing attention, broken, or not being tracked.
    for ticket in list(zen_tickets):

        # Add Zendesk data to enhancement data object
        for field in ticket['fields']:
            if field['id'] == zen_fieldid:
                association_data = field['value']
                break
        enhancement_data = {} # Enhancement data object
        enhancement_data['z_id'] = ticket['id']
        enhancement_data['z_requester'] = \
                zen_user_reference[ticket['requester_id']]
        enhancement_data['z_subject'] = ticket['subject']
        z_date = datetime.strptime(ticket['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
        z_date = z_date + timedelta(hours=utc_offset)
        enhancement_data['z_date'] = z_date.strftime('%m/%d/%Y @ %I:%M %p')
        
        # Check if it has no associated  GitHub ticket
        if association_data is None or \
           association_data.split('-')[0] != 'gh':
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
            enhancement_data['g_id'] = git_issue['number']
            enhancement_data['g_url'] = git_issue['html_url']
            enhancement_data['g_status'] = git_issue['state']
            g_date = datetime.strptime(git_issue['updated_at'], 
                                       "%Y-%m-%dT%H:%M:%SZ")
            g_date = g_date + timedelta(hours=utc_offset)
            enhancement_data['g_date'] = g_date.strftime('%m/%d/%Y @ %I:%M %p')
            
            # Check if the enhacement should be tracked (Both tickets are
            # open).
            if enhancement_data['g_status'] == 'open':
                tracking.append(enhancement_data)
            
            # Check if the enhancement is in need of attention (The GitHub
            # ticket is closed).
            else:
                need_attention.append(enhancement_data)
    
    built_data = {
        'tracking': tracking,
        'need_attention': need_attention,
        'broken_enhancements': broken_enhancements,
        'unassociated_enhancements': unassociated_enhancements,
    }

    return built_data

def request_unsuccessful(request, responsible_api, error_details):
    """Renders the home page with the appropriate error message if an API
    request was unsuccessful.

    Parameters:
        request - The request object with the necessary context to render the
                    home page.
        responsible_api - A string of the name of the API that was
                            unsuccessfully connected to.
        error_details - A string of the error message or error details
                            associated with the unsuccessful API request.
    """
    error_message = 'There was an error connecting to the %s API - %s. Try \
                    adjusting your account settings.' % (responsible_api,
                                                         error_details)
    render_data = {'api_requests_successful': False,
                   'error_message': error_message}

    return render_to_response('home.html', render_data,
                                context_instance=RequestContext(request))
