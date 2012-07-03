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
from requests_oauth2 import OAuth2
from datetime import datetime, timedelta

# Constant URL string for accessing the GitHub API. The first %s is the
# organization/user name, the second %s is the repository name, and the thrid %s
# is the issue number of the ticket being accessed.
ISSUE_GIT_URL = 'https://api.github.com/repos/%s/%s/issues/%s'

# Constant OAuth handler and authorization URL for access to GitHub's OAuth.
OAUTH2_HANDLER = OAuth2(CLIENT_ID, CLIENT_SECRET, site='https://github.com/',
                        redirect_uri='http://gitzen.herokuapp.com/git_confirm',
                        authorization_url='login/oauth/authorize',
                        token_url='login/oauth/access_token')
GIT_AUTH_URL = OAUTH2_HANDLER.authorize_url('repo')

# Constant URL string for searching for tickets through the Zendesk API. The %s
# is the custom URL subdomain for the specific company whose tickets are being
# accessed.
SEARCH_ZEN_URL = '%s/api/v2/search.json'

# Constant search query used to access open Zendesk problem and incident tickets
# form its API.
ZTIC_SEARCH_QUERY = 'type:ticket ticket_type:incident ticket_type:problem \
                        status:open'

# Constant URL string for accessing Zendesk users through the Zendesk API. The
# first %s if the custom URL subdomain for the specific company whose users are
# being accessed, and the second %s is the ID number of the user being accessed.
USER_ZEN_URL = '%s/api/v2/users/%s.json'

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
    render_data = {} # Data to be rendered to the home page

    zen_tics = [] # List of the open problem or incident tickets in Zendesk.
    zen_user_ref = {} # Dictionary reference of the user IDs and user names
                      # associated with the Zendesk tickets in zen_tics.
    git_tics = [] # List of the GitHub tickets associated with the Zendesk
                  # tickets in zen_tics.
    # Status booleans for each of the previous three collections. They will be
    # set as True if the cooresponding collection was successfully gathered.
    ztic_status = False
    zuser_status = False
    gtic_status = False

    zen_tics, ztic_status = get_zen_tickets(profile)
    if ztic_status:
        user_ids, git_nums = get_id_lists(zen_tics, zen_fieldid)
        zen_user_ref, zuser_status = get_zen_users(profile, user_ids)
        git_tics, gtic_status = get_git_tickets(profile, git_nums)

    api_status = ztic_status and zuser_status and gtic_status
    render_data = build_enhancement_data(zen_tics, zen_user_ref, git_tics, 
                                         zen_fieldid, api_status)

    # Add additional user data to be rendered to the home page
    render_data['zen_url'] = profile.zen_url
    
    return render_to_response('home.html', render_data,
                                context_instance=RequestContext(request))

def get_zen_tickets(profile):
    """Gets all of the open problem and incident Zendesk tickets using the
    Zendesk API.

    Parameters:
        profile - The profile object that contains the current user's data 
                    necessary to access the tickets on their Zendesk account.

    Returns a tuple of two values with the first value being the gathered list
    of Zendesk tickets and with the second value being the status of that list
    (True if the API calls were all successful, False if not).
    """
    zen_name_tk = profile.zen_name + '/token' # Zendesk user email set up for 
                                              # API token authorization.
    zticket_list = []
    page = 1

    try:
        while True:
            r_zt = requests.get(SEARCH_ZEN_URL % profile.zen_url, 
                                params={'query': ZTIC_SEARCH_QUERY,
                                        'sort_by': 'updated_at',
                                        'sort_order': 'desc',
                                        'per_page': 100,
                                        'page': page},
                                auth=(zen_name_tk, profile.zen_token))
            if r_zt.status_code != 200:
                raise Exception('Error in accessing Zendesk API - %s' % \
                                r_zt.json['error'])
            zticket_list.extend(r_zt.json['results'])
            if r_zt.json['next_page'] is not None:
                page += 1
            else:
                break
        
        ztic_status = True
    except:
        ztic_status = False

    return (zticket_list, ztic_status)

def get_id_lists(zen_tics, zen_fieldid):
    """Gets lists of the Zendesk user IDs and the GitHub issue numbers that are
    associated with the passed list of Zendesk tickets.

    Parameters:
        zen_tics - A list of Zendesk tickets whose associated GitHub issue
                    numbers and Zendesk user IDs are desired.
        zen_fieldid - The ID number of the custom field in Zendesk tickets that
                        holds its associated GitHub issue number.

    Returns a tuple of two value with the first being the gathered list of
    associated Zendesk user IDs and with the second being the gathered list
    of associated GitHub issue numbers.
    """
    
    # Get Zendesk user IDs that are associated with Zendesk tickets.
    user_ids = []
    for t in zen_tics:
        user_ids.append(t['requester_id'])
    user_ids = list(set(user_ids)) # Remove duplicates
    
    # Get GitHub issue numbers that are associated with the Zendesk tickets.
    git_nums = []
    for t in zen_tics:
        for f in t['fields']:
            if f['id'] == zen_fieldid:
                if f['value'] is not None:
                    a_num = f['value'].split('-') # Association number
                else:
                    a_num = ['']
                break
        if a_num[0] == 'gh':
            git_nums.append(int(a_num[1]))
    git_nums = list(set(git_nums)) # Remove duplicates

    return (user_ids, git_nums)

def get_zen_users(profile, user_ids):
    """Gets the full Zendesk user records for each user ID number in the passed
    list.

    Parameters:
        profile - The profile object that contains the current user's data
                    necessary to access the users on their Zendesk account.  
        user_ids - A list of Zendesk user IDs whose full user records are 
                    desired.

    Returns a tuple of two values with the first being a dictionary reference
    table with Zendesk user ID numbers as keys and the cooresponding user names
    as the values and with the second being the status of that dictionary (True
    if the API calls were all successful, False if not).
    """
    zen_name_tk = profile.zen_name + '/token' # Zendesk user email set up for 
                                              # API token authorization.
    zuser_ref = {} # Dictionary where the

    try:
        for id_num in user_ids:
            r_zu = requests.get(USER_ZEN_URL % (profile.zen_url, id_num),
                                auth=(zen_name_tk, profile.zen_token))
            if r_zu.status_code != 200:
                raise Exception('Error in accessing Zendesk API - %s' % \
                                r_zu.json['error'])
            zuser_ref[id_num] = r_zu.json['user']['name']
        
        zuser_status = True
    except:
        zuser_status = False

    return (zuser_ref, zuser_status)

def get_git_tickets(profile, git_nums):
    """Gets the full GitHub ticket records for each issue number in the passed
    list.

    Parameters:
        profile - The profile object that contains the current user's data
                    necessary to access the tickets on their GitHub account.  
        git_nums - A list of GitHub issue numbers whose full ticket records are 
                    desired.

    Returns a tuple of two values with the first being a list with a GitHub
    ticket record for each of the issue numbers passed to the function and with
    the second being the status of that list (True if the API calls were all
    successful, False if not).
    """
    gticket_list = []

    try:
        for num in git_nums:
            r_gt = requests.get(ISSUE_GIT_URL % (profile.git_org, 
                                                profile.git_repo, num),
                                params={'access_token': profile.git_token}
                               )
            if r_gt.status_code != 200:
                raise Exception('Error in accessing GitHub API - %s' % \
                                r_gt.json['message'])
            gticket_list.extend(r_gt.json)

        gtic_status = True
    except:
        gtic_status = False

    return (gticket_list, gtic_status)

def build_enhancement_data(zen_tics, zen_user_ref, git_tics, zen_fieldid,
                           api_status):
    """Builds the enhancement tracking tables from the Zendesk and GitHub data.
    
    Parameters:
        zen_tics - A list of open Zendesk tickets to build the enhancement
                    data from.
        zen_user_ref - A dictionary reference that can be used to look up
                        Zendesk user names by their ID number.
        git_tics - A list of GitHub tickets that cooresponds with the associated
                    GitHub issue numbers of the Zendesk tickets in zen_tics.
        zen_fieldid - The ID number of the custom field that holds the ticket
                        association value for a given Zendesk ticket.
        api_status - A boolean that is True if the API lists were successfully
                        gathered, and False if they were not. Needed to
                        determine the status of the enhancement tracking lists.

    Returns a dictionary of the built data with the following keys and values:
        'tracking' - List of enhancements in the process of being worked on.
        'need_attention' - List of enhancements where one half of the
                            enhancement is completed, but the other is not.
        'broken_enh' - List of Zendesk tickets that have improper data in their
                            GitHub issue association field. This could be the
                            result of a typo or some other user error.
        'not_tracking' - List of Zendesk tickets requesting an enhancement that
                            have no associated ticket in GitHub.
    """
    tracking = [] # Enhancements whose Zendesk and GitHub tickets are both open.
    need_attention = [] # Enhancements with either a closed Zendesk ticket or
                        # a closed GitHub ticket. Because one of these tickets
                        # is closed, the other needs attention.
    broken_enhancements = [] # Requested enhancements from Zendesk with a broken
                             # GitHub issue association field.
    not_tracking = [] # Requested enhancements from Zendesk tickets that have no
                      # associatied GitHub ticket assigned to them.
    if api_status:

        # Iterate through the Zendesk tickets using their data to classify them
        # as being tracked, needing attention, broken, or not being tracked.
        for t in list(zen_tics):

            # Add Zendesk data to enhancement data object
            for f in t['fields']:
                if f['id'] == zen_fieldid:
                    a_num = f['value'] # Association number
                    break
            e_data = {} # Enhancement data object
            e_data['z_id'] = t['id']
            e_data['z_user'] = zen_user_ref[t['requester_id']]
            e_data['z_subject'] = t['subject']
            z_date = datetime.strptime(t['updated_at'], 
                                        "%Y-%m-%dT%H:%M:%SZ")
            e_data['z_date'] = z_date.strftime('%m/%d/%Y @ %H:%M')
            
            # Check if it has no associated GitHub ticket
            if a_num is None or a_num.split('-')[0] != 'gh':
                not_tracking.append(e_data)
            
            else:
                # Add GitHub data to enhancement data object
                git_issue = {}
                for i in git_tics:
                    if i['number'] == int(a_num.split('-')[1]):
                        git_issue = i
                        break
                # Check if it has a broken GitHub association field
                if not git_issue:
                    e_data['broken_assoc'] = a_num
                    broken_enhancements.append(e_data)
                    continue
                e_data['g_id'] = git_issue['number']
                e_data['g_labels'] = [i['name'] for i in git_issue['labels']]
                e_data['g_url'] = git_issue['html_url']
                e_data['g_status'] = git_issue['state']
                g_date = datetime.strptime(git_issue['updated_at'], 
                                            "%Y-%m-%dT%H:%M:%SZ")
                e_data['g_date'] = g_date.strftime('%m/%d/%Y @ %H:%M')
                
                # Check if the enhacement should be tracked (Both tickets are
                # open).
                if e_data['g_status'] == 'open':
                    tracking.append(e_data)
                
                # Check if the enhancement is in need of attention (The GitHub
                # ticket is closed).
                else:
                    need_attention.append(e_data)
    
    built_data = {
        'tracking': tracking,
        'need_attention': need_attention,
        'broken_enh': broken_enhancements,
        'not_tracking': not_tracking
    }

    return built_data
