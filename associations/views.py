from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login, logout
from django import forms
from associations.models import GZUser
import requests
from datetime import datetime, timedelta

class LogForm(forms.Form):
    """Form for login of an existing user."""

    username = forms.CharField(max_length=75)
    password = forms.CharField(max_length=75, widget=forms.PasswordInput)

class NewForm(forms.Form):
    """Form for creating a new user."""

    username = forms.CharField(max_length=75)
    password = forms.CharField(max_length=75, widget=forms.PasswordInput)
    affirmpass = forms.CharField(max_length=75, widget=forms.PasswordInput)
    git_name = forms.CharField(max_length=75)
    git_pass = forms.CharField(max_length=75, widget=forms.PasswordInput)
    git_org = forms.CharField(max_length=75)
    git_repo = forms.CharField(max_length=75)
    zen_name = forms.CharField(max_length=75)
    zen_token = forms.CharField(max_length=75, widget=forms.PasswordInput)
    zen_url = forms.CharField(max_length=100)
    zen_fieldid = forms.CharField(max_length=50)

class ChangeForm(forms.Form):
    """Form for changing the data of an existing user."""

    old_pass = forms.CharField(max_length=75, widget=forms.PasswordInput,
                               required=False)
    new_pass = forms.CharField(max_length=75, widget=forms.PasswordInput,
                               required=False)
    aff_pass = forms.CharField(max_length=75, widget=forms.PasswordInput,
                               required=False)
    git_name = forms.CharField(max_length=75, required=False)
    git_pass = forms.CharField(max_length=75, widget=forms.PasswordInput, 
                               required=False)
    git_org = forms.CharField(max_length=75, required=False)
    git_repo = forms.CharField(max_length=75, required=False)
    zen_name = forms.CharField(max_length=75, required=False)
    zen_token = forms.CharField(max_length=75, widget=forms.PasswordInput,
                               required=False)
    zen_url = forms.CharField(max_length=100, required=False)
    zen_fieldid = forms.CharField(max_length=50, required=False)


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
                    return HttpResponseRedirect('/home/')
                else:
                    return HttpResponseRedirect('/nope/1/')
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
                    user.save()

                    return HttpResponseRedirect('/confirm/1')
                else:
                    return HttpResponseRedirect('/nope/2/')
            logform = LogForm()
    else:
        logform = LogForm()
        newform = NewForm()

    return render_to_response('associations/login.html', {'logform': logform,
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
                        return HttpResponseRedirect('/nope/4')
                else:
                    return HttpResponseRedirect('/nope/3')
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
            user.save()

            return HttpResponseRedirect('/confirm/2')
    else:
        changeform = ChangeForm()
    
    return render_to_response('associations/change.html', 
                                {'changeform': changeform,},
                                context_instance=RequestContext(request))


def nope(request, nope_num):
    """Renders the error page if there is an issue in the submitted data from
    the different forms.

    Parameters:
        request - The request object sent with the call to render the page. Not
                    used in this function.
        nope_num - The number to identify which error message should be 
                    displayed on the page.
    """
    return render_to_response('associations/nope.html', 
                                {'nope_num': nope_num,})

def confirm(request, con_num):
    """Renders the confirmation page to confirm the successful submission of
    data from the different forms.

    Parameters:
        request - The request object sent with the call to render the page. Not
                    used in this function.
        con_num - The number to identify which confirmation message should be
                    displayed on the page.
    """
    return render_to_response('associations/confirm.html',
                                {'con_num': con_num,})


def home(request):
    """Gathers and builds the association data and renders the home page of the
    app with this data.
    
    Parameters:
        request - The request object that contains the current user's data.
    """
    api_lists = {} # Stores lists from API calls and their status
    filtered_lists = {} # Stores lists of the filtered API data
    render_data = {} # Data to be rendered to the home page
    
    api_lists = api_calls(request)
    filtered_lists = filter_lists(request.user.zen_fieldid, api_lists)

    api_status = api_lists['status']['git'] and api_lists['status']['zen']
    render_data = build_associations(request.user.zen_fieldid, filtered_lists,
                                    api_status)

    # Combine the status dictionaries from the API data and association lists
    render_data['status'] = dict(render_data['status'].items() +
                                 api_lists['status'].items())

    # Add additional user data to be rendered to the home page
    render_data['repo'] = request.user.git_repo
    render_data['zen_url'] = request.user.zen_url
    
    return render_to_response('associations/home.html', render_data,
                                context_instance=RequestContext(request))

def api_calls(request):
    """Makes API calls to GitHub and Zendesk to gather the data used in the app.
    
    Parameters:
        request - The request object that contains the current user's data.

    Returns a dictionary with the following keys and values:
        'gopen' - List of all of the open tickets in the GitHub repo
        'gclosed' - List of all of the closed tickets in the GitHub repo
        'ztickets' - List of all of the tickets on the Zendesk account
        'zusers' - List of all of the users (customers, admins, etc.) on the
                    Zendesk account
        'status' - Dictionary with the status of the API calls for GitHub and
                    Zendesk with the following keys and values:
            'git' - True if Git call was successful, False if not
            'zen' - True if Zen call was successful, False if not
    """
    user = request.user
    working = {}
    date_limit = datetime.now() - timedelta(days=180)
    limit_str = datetime.strftime(date_limit, '%Y-%m-%dT%H:%M:%SZ')

    try:  # GitHub API calls to get all open and closed tickets
        # Get GitHub open tickets
        gopen_list = []
        page = 1
        url = 'https://api.github.com/repos/%s/%s/issues?page=%s' % \
                            (user.git_org, user.git_repo, page)
        while True:
            r_op = requests.get(url,
                                params={'state': 'open', 'since': limit_str}, 
                                auth=(user.git_name, user.git_pass))
            gopen_list.extend(r_op.json)
            if r_op.json:
                page += 1
                url = 'https://api.github.com/repos/%s/%s/issues?page=%s' % \
                            (user.git_org, user.git_repo, page)
            else:
                break
        
        # Get GitHub closed tickets
        gclosed_list = []
        page = 1
        url = 'https://api.github.com/repos/%s/%s/issues?page=%s' % \
                            (user.git_org, user.git_repo, page)
        while True:
            r_cl = requests.get(url, 
                                params={'state': 'closed', 'since': limit_str},
                                auth=(user.git_name, user.git_pass))
            gclosed_list.extend(r_cl.json)
            if r_cl.json:
                page += 1
                url = 'https://api.github.com/repos/%s/%s/issues?page=%s' % \
                            (user.git_org, user.git_repo, page)
            else:
                break
         
        working['git'] = True
    except:
        working['git'] = False

    try:  # Zendesk API calls to get all tickets and users
        zen_name_tk = user.zen_name + '/token' #Zendesk user email set up for
                                               #API token authorization
        # Get Zendesk tickets
        zticket_list = []
        url = '%s/api/v2/tickets.json' % (user.zen_url)
        while True:
            r_zt = requests.get(url, auth=(zen_name_tk, user.zen_token))
            zticket_list.extend(r_zt.json['tickets'])
            if r_zt.json['next_page'] is not None:
                url = r_zt.json['next_page']
            else:
                break
        
        # Get Zendesk users
        zuser_list = []
        url = '%s/api/v2/users.json' % (user.zen_url)
        while True:
            r_zu = requests.get(url, auth=(zen_name_tk, user.zen_token))
            zuser_list.extend(r_zu.json['users'])
            if r_zu.json['next_page'] is not None:
                url = r_zu.json['next_page']
            else:
                break

        working['zen'] = True
    except:
        working['zen'] = False

    api_lists = {
        'gopen': gopen_list,
        'gclosed': gclosed_list,
        'ztickets': zticket_list,
        'zusers': zuser_list,
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
        'req_ref' - Reference table for looking up users by ID number.
        'ztics' - Filtered Zendesk ticket list with only the values needed in
                    the quick reference table.
        'ztics_full' - Filtered Zendesk ticket list with all values.
        'gtics' - Filtered GitHub ticket list
    """

    # Zendesk list filtering
    if data_lists['status']['zen']:

        # Builds a table (req_ref) that allows for quickly looking up a user's
        # name with their user ID.
        req_ref = {}
        id_nums = []
        for t in data_lists['ztickets']:
            if t['requester_id'] not in id_nums:
                id_nums.append(t['requester_id'])
        for i in id_nums:
            for u in data_lists['zusers']:
                if i == u['id']:
                    req_ref[i] = u['name']
                    break
        del id_nums
        
        # Filters the list of Zendesk tickets to remove closed tickets that are
        # not associated with GitHub. The filterd list is appended into two
        # different lists: one that includes only the attributes needed for the
        # quick reference table of the app display (zen_tics), and one that
        # includes all of the attributes for later use in building the
        # association lists (zen_tics_full).
        zen_tics = []
        zen_tics_full = []
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
                        'req_name': req_ref[t['requester_id']],
                        'subject': t['subject'],
                    })
    
    # GitHub list filtering
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
        git_tics.reverse() # List is reversed to put the oldest tickets first.

    filtered_lists = {
        'req_ref': req_ref,
        'ztics': zen_tics,
        'ztics_full': zen_tics_full,
        'gtics': git_tics
    }

    return filtered_lists

def build_associations(zen_fieldid, filtered_lists, api_status):
    """Builds the association tables from the Zendesk and GitHub data.
    
    Parameters:
        zen_fieldid - The ID number of the custom field that holds the ticket
                        association value for a given Zendesk ticket.
        filtered_lists - A dictionary including lists of GitHub tickets, Zendesk
                            tickets, and a Zendesk user reference table that
                            have all been filtered and contain only the
                            entries to be used in building associations.
        api_status - A boolean that is True if the API lists were successfully
                        gathered, and False if they were not. Needed to
                        determine the status of the association lists.

    Returns a dictionary of the built data with the following keys and values:
        'git_tics' - List of the GitHub tickets used in the app.
        'zen_tics' - List of the Zendesk tickets used in the app.
        'o_assocs' - List of open association data objects.
        'ho_assocs' - List of half-open association data objects
        'no_assocs' - List of association data objects with no associated GitHub
                        ticket.
        'status' - Dictionary with the status of building the association lists
                    with the following keys and values:
            'o_assocs' - True if the open association list was built
                            successfully, False if not.
            'ho_assocs' - True if the half-open association list was built
                            successfully, False if not.
            'no_assocs' - True if the no association list was built
                            successfully, False if not.
    """

    if api_status:
        o_assocs = [] # open associations
        ho_assocs = [] # half-open associations
        no_assocs = [] # no associations
        status = {}
        status['o_assocs'] = True
        status['ho_assocs'] = True
        status['no_assocs'] = True

        # The app will only display Zendesk tickets with no association up to
        # this far away from the current date.
        na_limit = timedelta(weeks=1)
        
        # Iterate through the Zendesk tickets using their data to classify them
        # into an open association, half-open association, or no associarion. If
        # the ticket does not fit into any of these catagories, it is deleted
        # form the list to be returned.
        for t in filtered_lists['ztics_full']:

            # Add Zendesk data to association data object
            for f in t['fields']:
                if f['id'] == int(zen_fieldid):
                    a_num = f['value']
                    break
            a_data = {} # Association data object
            a_data['z_id'] = t['id']
            a_data['z_user'] = filtered_lists['req_ref'][t['requester_id']]
            a_data['z_status'] = t['status']
            z_date = datetime.strptime(t['updated_at'], 
                                        "%Y-%m-%dT%H:%M:%SZ")
            a_data['z_date'] = z_date.strftime('%m/%d/%Y @ %H:%M')
            
            # Check if it has no associated ticket
            if a_num is None or a_num.split('-')[0] != 'gh':
                # Check if date is in the no association delta range
                if datetime.now() > z_date + na_limit:
                    for i in range(len(filtered_lists['ztics'])):
                        if filtered_lists['ztics'][i]['id'] == \
                           a_data['z_id']:
                            filtered_lists['ztics'].pop(i)
                            break
                
                else:
                    if a_num is None or a_num == '':
                        a_data['assoc'] = 'None'
                    else:
                        a_data['assoc'] = a_num
                    no_assocs.append(a_data)
            
            else:
                # Add GitHub data to association data object
                for i in filtered_lists['gtics']:
                    if i['number'] == int(a_num.split('-')[1]):
                        git_issue = i
                        break
                a_data['g_id'] = git_issue['number']
                a_data['g_user'] = git_issue['user']['login']
                a_data['g_labels'] = [i['name'] for i in git_issue['labels']]
                a_data['g_url'] = git_issue['html_url']
                a_data['g_status'] = git_issue['state']
                g_date = datetime.strptime(git_issue['updated_at'], 
                                            "%Y-%m-%dT%H:%M:%SZ")
                a_data['g_date'] = g_date.strftime('%m/%d/%Y @ %H:%M')
                
                # Check if the tickets have an open association (Both are open).
                if a_data['g_status'] == 'open' and \
                   a_data['z_status'] == 'open':
                    o_assocs.append(a_data)
                
                # Check if the tickets have a closed association (Both are
                # closed). These tickets are deleted from their lists.
                elif a_data['g_status'] != 'open' and \
                        a_data['z_status'] != 'open':
                    for i in range(len(filtered_lists['gtics'])):
                        if filtered_lists['gtics'][i]['number'] == \
                           a_data['g_id']:
                            filtered_lists['gtics'].pop(i)
                            break
                    for i in range(len(filtered_lists['ztics'])):
                        if filtered_lists['ztics'][i]['id'] == \
                           a_data['z_id']:
                            filtered_lists['ztics'].pop(i)
                            break
                
                # Check if the tickets have a half-open association (One is open
                # and one is closed).
                else:
                    if a_data['g_status'] == 'open':
                        a_data['closed'] = 'z'
                    else:
                        a_data['closed'] = 'g'
                    ho_assocs.append(a_data)
    else:
        status['o_assocs'] = False
        status['ho_assocs'] = False
        status['no_assocs'] = False
    
    built_data = {
        'git_tics': filtered_lists['gtics'],
        'zen_tics': filtered_lists['ztics'],
        'o_assocs': o_assocs,
        'ho_assocs': ho_assocs,
        'no_assocs': no_assocs,
        'status': status
    }

    return built_data
