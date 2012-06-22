from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login, logout
from django.core.urlresolvers import reverse
from enhancement_tracking.models import GZUser
from enhancement_tracking.forms import LogForm, NewForm, ChangeForm
import requests
from datetime import datetime, timedelta

# Constatn URL strings for accessing the GitHub API. The first %s is the
# organization/user name and the second %s is the repository name.
BASE_GIT_URL = 'https://api.github.com/repos/%s/%s/issues'

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
            logform = LogForm(request.POST)
            if logform.is_valid():
                user = authenticate(
                    username=logform.cleaned_data['username'],
                    password=logform.cleaned_data['password'],
                )

                if user is not None:
                    login(request, user)
                    return HttpResponseRedirect(reverse('home'))
                else:
                    return HttpResponseRedirect(reverse('nope', args=[1]))
            newform = NewForm()

        elif 'new' in request.POST:  # Process new user form
            newform = NewForm(request.POST)
            if newform.is_valid():
                data = newform.cleaned_data
                if data['password'] == data['affirmpass']:
                    user = GZUser.objects.create_user(
                        username=data['username'],
                        password=data['password'],
                        email='',
                    )
                    user.git_name = data['git_name']
                    user.git_pass = data['git_pass']
                    user.git_org = data['git_org']
                    user.git_repo = data['git_repo']
                    user.zen_name = data['zen_name']
                    user.zen_token = data['zen_token']
                    user.zen_url = data['zen_url']
                    user.zen_fieldid = data['zen_fieldid']
                    user.age_limit = data['age_limit']
                    user.save()

                    return HttpResponseRedirect(reverse('confirm', args=[1]))
                else:
                    return HttpResponseRedirect(reverse('nope', args=[2]))
            logform = LogForm()
    else:
        logform = LogForm()
        newform = NewForm()

    return render_to_response('login.html', {'logform': logform,
                                'newform': newform,}, 
                              context_instance=RequestContext(request))

def change(request):
    """Processes the requests from the Change Account Data page.

    All of the fields on the change form are optional so that the user can
    change only the account data that they want changed.

    Parameters:
        request - The request object that contains the POST data from the change
                    form.
    """

    if request.method == 'POST':
        changeform = ChangeForm(request.POST)
        if changeform.is_valid():
            data = changeform.cleaned_data
            user = request.user

            if data['new_pass']:
                if user.check_password(data['old_pass']):
                    if data['new_pass'] == data['aff_pass']:
                        user.set_password(data['new_pass'])
                    else:
                        return HttpResponseRedirect(reverse('nope', args=[4]))
                else:
                    return HttpResponseRedirect(reverse('nope', args=[3]))
            if data['git_name']:
                user.git_name = data['git_name']
            if data['git_pass']:
                user.git_key = data['git_pass']
            if data['git_org']:
                user.git_key = data['git_org']
            if data['git_repo']:
                user.git_repo = data['git_repo']
            if data['zen_name']:
                user.zen_name = data['zen_name']
            if data['zen_token']:
                user.zen_token = data['zen_token']
            if data['zen_url']:
                user.zen_url = data['zen_url']
            if data['zen_fieldid']:
                user.zen_fieldid = data['zen_fieldid']
            if data['age_limit']:
                user.age_limit = data['age_limit']
            user.save()

            return HttpResponseRedirect(reverse('confirm', args=[2]))
    else:
        changeform = ChangeForm()
    
    return render_to_response('change.html', 
                                {'changeform': changeform,},
                                context_instance=RequestContext(request))


def nope(request, nope_num):
    """Renders the error page if there is an issue in the submitted data from
    the different forms.

    Parameters:
        request - The request object sent with the call to render the page.
        nope_num - The number to identify which error message should be 
                    displayed on the page.
    """
    return render_to_response('nope.html', 
                                {'nope_num': nope_num,},
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
                              {'con_num': con_num,},
                              context_instance=RequestContext(request))


def home(request):
    """Gathers and builds the enhancement tracking data and renders the home
    page of the app with this data.
    
    Parameters:
        request - The request object that contains the current user's data.
    """
    api_lists = {} # Stores lists from API calls and their status
    filtered_lists = {} # Stores lists of the filtered API data
    render_data = {} # Data to be rendered to the home page
    
    api_lists = api_calls(request)
    filtered_lists = filter_lists(request.user.zen_fieldid, api_lists)

    api_status = api_lists['status']['git'] and api_lists['status']['zen']
    render_data = build_enhancement_data(request.user.zen_fieldid,
                                         filtered_lists, api_status)

    # Combine the status dictionaries from the API data and association lists
    render_data['status'] = dict(render_data['status'].items() +
                                 api_lists['status'].items())

    # Add additional user data to be rendered to the home page
    render_data['repo'] = request.user.git_repo
    render_data['zen_url'] = request.user.zen_url
    
    return render_to_response('home.html', render_data,
                                context_instance=RequestContext(request))

def api_calls(request):
    """Makes API calls to GitHub and Zendesk to gather the data used in the app.
    
    Parameters:
        request - The request object that contains the current user's data.

    Returns a dictionary with the following keys and values:
        'gopen' - List of all of the open tickets in the GitHub repo
        'gclosed' - List of all of the closed tickets in the GitHub repo
        'ztickets' - List of all of the tickets on the Zendesk account
        'status' - Dictionary with the status of the API calls for GitHub and
                    Zendesk with the following keys and values:
            'git' - True if Git call was successful, False if not
            'zen' - True if Zen call was successful, False if not
    """
    user = request.user
    working = {}

    # This line sets the limit for how far back the API calls go when
    # gathering tickets.
    date_limit = datetime.now() - timedelta(days=user.age_limit)

    # Git and Zen require the date_limit to be formatted differently
    git_limit_str = datetime.strftime(date_limit, '%Y-%m-%dT%H:%M:%SZ')
    zen_limit_str = datetime.strftime(date_limit, '%Y-%m-%d')

    try:  # GitHub API calls to get all open and closed tickets
        # Get GitHub open tickets
        gopen_list = []
        page = 1
        while True:
            r_op = requests.get(BASE_GIT_URL % (user.git_org, user.git_repo),
                                params={'state': 'open', 
                                        'since': git_limit_str,
                                        'per_page': 100,
                                        'page': page},
                                auth=(user.git_name, user.git_pass))
            if r_op.status_code != 200:
                raise Exception('Error in accessing GitHub API - %s' %
                                (r_op.json['message']))
            gopen_list.extend(r_op.json)
            if r_op.json:
                page += 1
            else:
                break
        
        # Get GitHub closed tickets
        gclosed_list = []
        page = 1
        while True:
            r_cl = requests.get(BASE_GIT_URL % (user.git_org, user.git_repo),
                                params={'state': 'closed', 
                                        'since': git_limit_str,
                                        'per_page': 100,
                                        'page': page},
                                auth=(user.git_name, user.git_pass))
            if r_op.status_code != 200:
                raise Exception('Error in accessing GitHub API - %s' %
                                (r_op.json['message']))
            gclosed_list.extend(r_cl.json)
            if r_cl.json:
                page += 1
            else:
                break
        
        working['git'] = True
    except:
        gopen_list = []
        gclosed_list = []
        working['git'] = False

    try:  # Zendesk API calls to get tickets
        zen_name_tk = user.zen_name + '/token' # Zendesk user email set up for
                                               # API token authorization.
        # Get Zendesk tickets
        zticket_list = []
        page = 1
        while True:
            r_zt = requests.get(BASE_ZEN_URL % user.zen_url, 
                                params={'query': SEARCH_QUERY % zen_limit_str,
                                        'sort_by': 'updated_at',
                                        'sort_order': 'desc',
                                        'per_page': 100,
                                        'page': page},
                                auth=(zen_name_tk, user.zen_token))
            if 'error' in r_zt.json:
                raise Exception('Error in accessing Zendesk API - %s: %s' %
                                (r_zt.json['error'], r_zt.json['description']))
            zticket_list.extend(r_zt.json['results'])
            if r_zt.json['next_page'] is not None:
                page += 1
            else:
                break
        
        working['zen'] = True
    except:
        zticket_list = []
        working['zen'] = False
    
    api_lists = {
        'gopen': gopen_list,
        'gclosed': gclosed_list,
        'ztickets': zticket_list,
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
        'ztics' - Filtered Zendesk ticket list with only the values needed in
                    the quick reference table.
        'ztics_full' - Filtered Zendesk ticket list with all values.
        'gtics' - Filtered GitHub ticket list
    """

    # Zendesk list filtering
    zen_tics = []
    zen_tics_full = []
    if data_lists['status']['zen']:
        # Filters the list of Zendesk tickets to remove closed tickets that are
        # not associated with GitHub. The filterd list is appended into two
        # different lists: one that includes only the attributes needed for the
        # quick reference table of the app display (zen_tics), and one that
        # includes all of the attributes for later use in building the
        # enhancement tracking lists (zen_tics_full).
        for t in data_lists['ztickets']:
            a_field = {}
            for f in t['fields']:
                if f['id'] == int(zen_fieldid):
                    a_field = f
                    break

            if a_field != {}:
                a_value = a_field['value']
                if not ((a_value == '' or a_value is None or \
                         a_value.split('-')[0] != 'gh') and \
                        t['status'] == 'closed'):
                    zen_tics_full.append(t)
                    zen_tics.append({
                        'id': t['id'],
                        'subject': t['subject'],
                    })
    
    # GitHub list filtering
    git_tics_sorted = []
    if data_lists['status']['git']:

        # Filters the list of closed GitHub tickets to remove the ones that are
        # not associated with any Zendesk ticket. This filtered list is then
        # combined with all of the open GitHub tickets.
        git_tics = []
        on_zen = []
        for t in zen_tics_full:
            for f in t['fields']:
                if f['id'] == int(zen_fieldid):
                    if f['value'] is not None:
                        a_num = f['value'].split('-')
                    else:
                        a_num = ['']
                    break
            if a_num[0] == 'gh':
                on_zen.append(int(a_num[1]))

        for t in data_lists['gclosed']:
            if t['number'] in on_zen:
                git_tics.append(t)
        del on_zen

        git_tics.extend(data_lists['gopen'])

        # Tickets are sorted into order by their issue number
        git_tics_sorted = sorted(git_tics, key=lambda k: k['number'])

    filtered_lists = {
        'ztics': zen_tics,
        'ztics_full': zen_tics_full,
        'gtics': git_tics_sorted
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
        'git_tics' - List of the GitHub tickets used in the app.
        'zen_tics' - List of the Zendesk tickets used in the app.
        'tracking' - List of enhancements in the process of being worked on.
        'need_attention' - List of enhancements where one half of the
                            enhancement is completed, but the other is not.
        'not_tracking' - List of Zendesk tickets requesting an enhancement that
                            have no associated ticket in GitHub.
        'status' - Dictionary with the status of building the enhancement lists
                    with the following keys and values:
            'tracking' - True if the open association list was built
                            successfully, False if not.
            'need_attention' - True if the half-open association list was built
                                successfully, False if not.
            'not_tracking' - True if the no association list was built
                                successfully, False if not.
    """
    
    status = {}
    tracking = [] # Enhancements whose Zendesk and GitHub tickets are both open.
    need_attention = [] # Enhancements with either a closed Zendesk ticket or
                        # a closed GitHub ticket. Because one of these tickets
                        # is closed, the other needs attention.
    not_tracking = [] # Requested enhancements from Zendesk tickets that have no
                      # associatied GitHub ticket assigned to them.
    if api_status:
        status['tracking'] = True
        status['need_attention'] = True
        status['not_tracking'] = True

        # Iterate through the Zendesk tickets using their data to classify them
        # as being tracked, needing attention, or not being tracked. If the
        # ticket does not fit into any of these catagories, it is deleted form
        # the list to be returned.
        for t in filtered_lists['ztics_full']:

            # Add Zendesk data to enhancement data object
            for f in t['fields']:
                if f['id'] == int(zen_fieldid):
                    a_num = f['value']
                    break
            e_data = {} # Enhancement data object
            e_data['z_id'] = t['id']
            e_data['z_status'] = t['status']
            z_date = datetime.strptime(t['updated_at'], 
                                        "%Y-%m-%dT%H:%M:%SZ")
            e_data['z_date'] = z_date.strftime('%m/%d/%Y @ %H:%M')
            
            # Check if it has no associated  GitHub ticket
            if a_num is None or a_num.split('-')[0] != 'gh':
                not_tracking.append(e_data)
            
            else:
                # Add GitHub data to enhancement data object
                for i in filtered_lists['gtics']:
                    if i['number'] == int(a_num.split('-')[1]):
                        git_issue = i
                        break
                e_data['g_id'] = git_issue['number']
                e_data['g_labels'] = [i['name'] for i in git_issue['labels']]
                e_data['g_url'] = git_issue['html_url']
                e_data['g_status'] = git_issue['state']
                g_date = datetime.strptime(git_issue['updated_at'], 
                                            "%Y-%m-%dT%H:%M:%SZ")
                e_data['g_date'] = g_date.strftime('%m/%d/%Y @ %H:%M')
                
                # Check if the enhacement should be tracked (Both tickets are
                # open).
                if e_data['g_status'] == 'open' and \
                   e_data['z_status'] == 'open':
                    tracking.append(e_data)
                
                # Check if the enhancement is already completed (Both tickets
                # are closed). These tickets are deleted from their lists.
                elif e_data['g_status'] != 'open' and \
                        e_data['z_status'] != 'open':
                    for i in range(len(filtered_lists['gtics'])):
                        if filtered_lists['gtics'][i]['number'] == \
                           e_data['g_id']:
                            filtered_lists['gtics'].pop(i)
                            break
                    for i in range(len(filtered_lists['ztics'])):
                        if filtered_lists['ztics'][i]['id'] == \
                           e_data['z_id']:
                            filtered_lists['ztics'].pop(i)
                            break
                
                # Check if the enhancement is in need of attention (One ticket
                # is open and the other is closed).
                else:
                    if e_data['g_status'] == 'open':
                        e_data['closed'] = 'z'
                    else:
                        e_data['closed'] = 'g'
                    need_attention.append(e_data)
    else:
        status['tracking'] = False
        status['need_attention'] = False
        status['not_tracking'] = False
    
    built_data = {
        'git_tics': filtered_lists['gtics'],
        'zen_tics': filtered_lists['ztics'],
        'tracking': tracking,
        'need_attention': need_attention,
        'not_tracking': not_tracking,
        'status': status
    }

    return built_data
