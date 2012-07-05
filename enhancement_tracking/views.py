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
# organization/user name and the second %s is the repository name.
BASE_GIT_URL = 'https://api.github.com/repos/%s/%s/issues'

# Constant OAuth handler and authorization URL for access to GitHub's OAuth.
OAUTH2_HANDLER = OAuth2(CLIENT_ID, CLIENT_SECRET, site='https://github.com/',
                        redirect_uri='http://gitzen.herokuapp.com/git_confirm',
                        authorization_url='login/oauth/authorize',
                        token_url='login/oauth/access_token')
GIT_AUTH_URL = OAUTH2_HANDLER.authorize_url('repo')

# Constant URL string for accessing the Zendesk API. The %s is the custom URL
# for the specific company whose tickets are being accessed.
BASE_ZEN_URL = '%s/api/v2/search.json'

# Constant search query used to access Zendesk tickets form its API. The %s is
# the oldest date (in the format YYYY/MM/DD) a ticket can be and still be
# included in the results.
SEARCH_QUERY = 'type:ticket updated>%s ticket_type:incident \
                ticket_type:problem'

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
    profile = request.user.get_profile()
    api_lists = {} # Stores lists from API calls and their status
    filtered_lists = {} # Stores lists of the filtered API data
    render_data = {} # Data to be rendered to the home page
    
    api_lists = api_calls(request)
    filtered_lists = filter_lists(profile.zen_fieldid, api_lists)

    api_status = api_lists['status']['git'] and api_lists['status']['zen']
    render_data = build_enhancement_data(profile.zen_fieldid,
                                         filtered_lists, api_status)

    # Combine the status dictionaries from the API data and association lists
    render_data['status'] = dict(render_data['status'].items() +
                                 api_lists['status'].items())

    # Add additional user data to be rendered to the home page
    render_data['repo'] = profile.git_repo
    render_data['zen_url'] = profile.zen_url
    
    return render_to_response('home.html', render_data,
                                context_instance=RequestContext(request))

def api_calls(request):
    """Makes API calls to GitHub and Zendesk to gather the data used in the app.
    
    Parameters:
        request - The request object that contains the current user's data.

    Returns a dictionary with the following keys and values:
        'git_open' - List of all of the open tickets in the GitHub repo
        'git_closed' - List of all of the closed tickets in the GitHub repo
        'zen_tickets' - List of all of the tickets on the Zendesk account
        'status' - Dictionary with the status of the API calls for GitHub and
                    Zendesk with the following keys and values:
            'git' - True if Git call was successful, False if not
            'zen' - True if Zen call was successful, False if not
    """
    profile = request.user.get_profile()
    working = {}

    # This line sets the limit for how far back the API calls go when
    # gathering tickets.
    date_limit = datetime.now() - timedelta(days=profile.age_limit)

    # Git and Zen require the date_limit to be formatted differently
    git_limit_str = datetime.strftime(date_limit, '%Y-%m-%dT%H:%M:%SZ')
    zen_limit_str = datetime.strftime(date_limit, '%Y-%m-%d')

    try:  # GitHub API calls to get all open and closed tickets
        # Get GitHub open tickets
        git_open_tickets = []
        page = 1
        while True:
            request_open_tickets = requests.get(BASE_GIT_URL % 
                                                (profile.git_org, 
                                                 profile.git_repo),
                                params={'access_token': profile.git_token,
                                        'state': 'open', 
                                        'since': git_limit_str,
                                        'per_page': 100,
                                        'page': page}
                               )
            if request_open_tickets.status_code != 200:
                raise Exception('Error in accessing GitHub API - %s' %
                                (request_open_tickets.json['message']))
            git_open_tickets.extend(request_open_tickets.json)
            if request_open_tickets.json:
                page += 1
            else:
                break
        
        # Get GitHub closed tickets
        git_closed_tickets = []
        page = 1
        while True:
            request_closed_tickets = requests.get(BASE_GIT_URL % 
                                                (profile.git_org,
                                                profile.git_repo),
                                params={'access_token': profile.git_token,
                                        'state': 'closed', 
                                        'since': git_limit_str,
                                        'per_page': 100,
                                        'page': page},
                               )
            if request_closed_tickets.status_code != 200:
                raise Exception('Error in accessing GitHub API - %s' %
                                (request_closed_tickets.json['message']))
            git_closed_tickets.extend(request_closed_tickets.json)
            if request_closed_tickets.json:
                page += 1
            else:
                break
        
        working['git'] = True
    except:
        git_open_tickets = []
        git_closed_tickets = []
        working['git'] = False

    try:  # Zendesk API calls to get tickets
        zen_name_tk = profile.zen_name + '/token' # Zendesk user email set up 
                                                  # for API token authorization.
        # Get Zendesk tickets
        zen_tickets = []
        page = 1
        while True:
            request_zen_tickets = requests.get(BASE_ZEN_URL % profile.zen_url, 
                                params={'query': SEARCH_QUERY % zen_limit_str,
                                        'sort_by': 'updated_at',
                                        'sort_order': 'desc',
                                        'per_page': 100,
                                        'page': page},
                                auth=(zen_name_tk, profile.zen_token))
            if 'error' in request_zen_tickets.json:
                raise Exception('Error in accessing Zendesk API - %s: %s' %
                                (request_zen_tickets.json['error'],
                                 request_zen_tickets.json['description']))
            zen_tickets.extend(request_zen_tickets.json['results'])
            if request_zen_tickets.json['next_page'] is not None:
                page += 1
            else:
                break
        
        working['zen'] = True
    except:
        zen_tickets = []
        working['zen'] = False
    
    api_lists = {
        'git_open': git_open_tickets,
        'git_closed': git_closed_tickets,
        'zen_tickets': zen_tickets,
        'status': working
    }

    return api_lists

def filter_lists(zen_fieldid, data_lists):
    """Filters GitHub and Zendesk data to remove the data not needed in the app.
    
    Parameters:
        zen_fieldid - The ID number of the custom field that holds the ticket
                        association value for a given Zendesk ticket.
        data_lists - The dictionary of lists that holds the GitHub ticket,
                        Zendesk ticket, Zendesk user, and status information 
                        that needs filtering.

    Returns a dictionary with the following keys and values:
        'zen_tickets' - Filtered Zendesk ticket list with only the values needed
                            in the quick reference table.
        'zen_tickets_full' - Filtered Zendesk ticket list with all values.
        'git_tickets' - Filtered GitHub ticket list
    """

    # Zendesk list filtering
    zen_tickets = []
    zen_tickets_full = []
    if data_lists['status']['zen']:
        # Filters the list of Zendesk tickets to remove closed tickets that are
        # not associated with GitHub. The filterd list is appended into two
        # different lists: one that includes only the attributes needed for the
        # quick reference table of the app display (zen_tics), and one that
        # includes all of the attributes for later use in building the
        # enhancement tracking lists (zen_tics_full).
        for ticket in data_lists['zen_tickets']:
            association_field = {}
            for field in t['fields']:
                if f['id'] == zen_fieldid:
                    association_field = f
                    break

            if association_field != {}:
                association_value = association_field['value']
                if not ((association_value == '' or \
                         association_value is None or \
                         association_value.split('-')[0] != 'gh') and \
                        t['status'] == 'closed'):
                    zen_tickets_full.append(ticket)
                    zen_tickets.append({
                        'id': ticket['id'],
                        'subject': ticket['subject'],
                    })
    
    # GitHub list filtering
    git_tickets = []
    if data_lists['status']['git']:

        # Filters the list of closed GitHub tickets to remove the ones that are
        # not associated with any Zendesk ticket. This filtered list is then
        # combined with all of the open GitHub tickets.
        git_issues_on_zen = []
        for ticket in zen_tickets_full:
            for field in ticket['fields']:
                if field['id'] == zen_fieldid:
                    if field['value'] is not None:
                        association_number = field['value'].split('-')
                    else:
                        association_number = ['']
                    break
            if association_number[0] == 'gh':
                git_issues_on_zen.append(int(association_number[1]))

        for ticket in data_lists['git_closed']:
            if ticket['number'] in git_issues_on_zen:
                git_tickets.append(t)
        del git_issues_on_zen

        git_tickets.extend(data_lists['git_open'])

    # Tickets are sorted into order by their issue/id number
    if zen_tickets:
        zen_tickets = sorted(zen_tickets, key=lambda k: k['id'])
    if git_tickets:
        git_tickets = sorted(git_tickets, key=lambda k: k['number'])

    filtered_lists = {
        'zen_tickets': zen_tickets,
        'zen_tickets_full': zen_tickets_full,
        'git_tickets': git_tickets
    }

    return filtered_lists

def build_enhancement_data(zen_fieldid, filtered_lists, api_status):
    """Builds the enhancement tracking tables from the Zendesk and GitHub
    association data.
    
    Parameters:
        zen_fieldid - The ID number of the custom field that holds the ticket
                        association value for a given Zendesk ticket.
        filtered_lists - A dictionary including lists of GitHub tickets, Zendesk
                            tickets, and a Zendesk user reference table that
                            have all been filtered and contain only the
                            entries to be used in building enhancement tracking
                            data.
        api_status - A boolean that is True if the API lists were successfully
                        gathered, and False if they were not. Needed to
                        determine the status of the enhancement tracking lists.

    Returns a dictionary of the built data with the following keys and values:
        'git_tickets' - List of the GitHub tickets used in the app.
        'zen_tickets' - List of the Zendesk tickets used in the app.
        'tracking' - List of enhancements in the process of being worked on.
        'need_attention' - List of enhancements where one half of the
                            enhancement is completed, but the other is not.
        'broken_enhancements' - List of Zendesk tickets that have improper data
                                    in their GitHub issue association field.
                                    This could be the result of a typo or some
                                    other user error.
        'not_tracking' - List of Zendesk tickets requesting an enhancement that
                            have no associated ticket in GitHub.
        'status' - Dictionary with the status of building the enhancement lists
                    with the following keys and values:
            'tracking' - True if the tracking list was built successfully, 
                            False if not.
            'need_attention' - True if the need attention list was built
                                successfully, False if not.
            'broken_enh' - True if the broken enhancements list was built
                                successfully, False if not. 
            'not_tracking' - True if the not tracking list was built
                                successfully, False if not.
    """
    
    status = {}
    tracking = [] # Enhancements whose Zendesk and GitHub tickets are both open.
    need_attention = [] # Enhancements with either a closed Zendesk ticket or
                        # a closed GitHub ticket. Because one of these tickets
                        # is closed, the other needs attention.
    broken_enhancements = [] # Requested enhancements from Zendesk with a broken
                             # GitHub issue association field.
    not_tracking = [] # Requested enhancements from Zendesk tickets that have no
                      # associatied GitHub ticket assigned to them.
    if api_status:
        status['tracking'] = True
        status['need_attention'] = True
        status['broken_enhancments'] = True
        status['not_tracking'] = True

        # Iterate through the Zendesk tickets using their data to classify them
        # as being tracked, needing attention, or not being tracked. If the
        # ticket does not fit into any of these catagories, it is deleted form
        # the list to be returned.
        for ticket in filtered_lists['zen_tickets_full']:

            # Add Zendesk data to enhancement data object
            for field in ticket['fields']:
                if field['id'] == zen_fieldid:
                    association_number = field['value']
                    break
            enhancement_data = {} # Enhancement data object
            enhancement_data['z_id'] = ticket['id']
            enhancement_data['z_status'] = ticket['status']
            enhancement_data['z_subject'] = ticket['subject']
            z_date = datetime.strptime(ticket['updated_at'], 
                                        "%Y-%m-%dT%H:%M:%SZ")
            enhancement_data['z_date'] = z_date.strftime('%m/%d/%Y @ %H:%M')
            
            # Check if it has no associated  GitHub ticket
            if association_number is None or \
               association_number.split('-')[0] != 'gh':
                not_tracking.append(enhancement_data)
            
            else:
                # Add GitHub data to enhancement data object
                git_issue = {}
                for issue in filtered_lists['git_tickets']:
                    if issue['number'] == int(association_number.split('-')[1]):
                        git_issue = issue
                        break
                # Check if it has a broken GitHub association field
                if not git_issue:
                    enhancement_data['broken_assoc'] = association_number
                    broken_enhancements.append(enhancement_data)
                    continue
                enhancement_data['g_id'] = git_issue['number']
                enhancement_data['g_labels'] = [label['name'] for label \
                                                in git_issue['labels']]
                enhancement_data['g_url'] = git_issue['html_url']
                enhancement_data['g_status'] = git_issue['state']
                g_date = datetime.strptime(git_issue['updated_at'], 
                                            "%Y-%m-%dT%H:%M:%SZ")
                enhancement_data['g_date'] = g_date.strftime('%m/%d/%Y @ %H:%M')
                
                # Check if the enhacement should be tracked (Both tickets are
                # open).
                if enhancement_data['g_status'] == 'open' and \
                   enhancement_data['z_status'] == 'open':
                    tracking.append(enhancement_data)
                
                # Check if the enhancement is already completed (Both tickets
                # are closed). These tickets are deleted from their lists.
                elif enhancement_data['g_status'] != 'open' and \
                        enhancement_data['z_status'] != 'open':
                    for i in range(len(filtered_lists['git_tickets'])):
                        if filtered_lists['git_tickets'][i]['number'] == \
                           enhancement_data['g_id']:
                            filtered_lists['git_tickets'].pop(i)
                            break
                    for i in range(len(filtered_lists['zen_tickets'])):
                        if filtered_lists['zen_tickets'][i]['id'] == \
                           enhancement_data['z_id']:
                            filtered_lists['zen_tickets'].pop(i)
                            break
                
                # Check if the enhancement is in need of attention (One ticket
                # is open and the other is closed).
                else:
                    if enhancement_data['g_status'] == 'open':
                        enhancement_data['closed'] = 'z'
                    else:
                        enhancement_data['closed'] = 'g'
                    need_attention.append(enhancement_data)
    else:
        status['tracking'] = False
        status['need_attention'] = False
        status['broken_enhancements'] = False
        status['not_tracking'] = False
    
    built_data = {
        'git_tickets': filtered_lists['git_tickets'],
        'zen_tickets': filtered_lists['zen_tickets'],
        'tracking': tracking,
        'need_attention': need_attention,
        'broken_enhancements': broken_enhancements,
        'not_tracking': not_tracking,
        'status': status
    }

    return built_data
