from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login, logout
from django import forms
from associations.models import GZUser
import requests

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
    """

    if request.method == 'POST':  # Process login form
        if 'log' in request.POST:
            logform = LogForm(request.POST)
            if logform.is_valid():
                user = authenticate(
                    username=logform.cleaned_data['username'],
                    password=logform.cleaned_data['password'],
                )

                if user is not None:
                    login(request, user)
                    return HttpResponseRedirect('/main/')
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
    """Renders the error page if there are issues in the submitted data from the
    different forms.
    """
    return render_to_response('associations/nope.html', 
                                {'nope_num': nope_num,})

def confirm(request, con_num):
    """Renders the confirmation page to confirm the successful submission of
    data from the different forms.
    """
    return render_to_response('associations/confirm.html',
                                {'con_num': con_num,})


def home(request):
    user = request.user
    working = {}

    try:
        gopen_list = []
        page = 1
        url = 'https://api.github.com/repos/%s/%s/issues?page=%s' % \
                            (user.git_org, user.git_repo, page)
        while True:
            r_op = requests.get(url, params={'state': 'open'},
                            auth=(user.git_name, user.git_pass))
            gopen_list.extend(r_op.json)
            if r_op.json:
                page += 1
                url = 'https://api.github.com/repos/%s/%s/issues?page=%s' % \
                            (user.git_org, user.git_repo, page)
            else:
                break
            
        gclosed_list = []
        page = 1
        url = 'https://api.github.com/repos/%s/%s/issues?page=%s' % \
                            (user.git_org, user.git_repo, page)
        while True:
            r_cl = requests.get(url, params={'state': 'closed'},
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

    try:
        zen_name_tk = user.zen_name + '/token' #Zen user email set up for
                                               #API token authorization
        zticket_list = []
        url = '%s/api/v2/tickets.json' % (user.zen_url)
        while True:
            r_zt = requests.get(url, auth=(zen_name_tk, user.zen_token))
            zticket_list.extend(r_zt.json['tickets'])
            if r_zt.json['next_page'] is not None:
                url = r_zt.json['next_page']
            else:
                break

        zuser_list = []
        url = '%s/api/v2/users.json' % (user.zen_url)
        while True:
            r_zu = requests.get(url, auth=(zen_name_tk, user.zen_token))
            zuser_list.extend(r_zu.json['users'])
            if r_zu.json['next_page'] is not None:
                url = r_zu.json['next_page']
            else:
                break

        zorg_list = []
        url = '%s/api/v2/organizations.json' % (user.zen_url)
        while True:
            r_zo = requests.get(url, auth=(zen_name_tk, user.zen_token))
            zorg_list.extend(r_zo.json['organizations'])
            if r_zo.json['next_page'] is not None:
                url = r_zo.json['next_page']
            else:
                break
        
        working['zen'] = True
    except:
        working['zen'] = False
         
    if working['zen']:
        req_ref = {}
        id_nums = []
        for t in zticket_list:
            if t['requester_id'] not in id_nums:
                id_nums.append(t['requester_id'])
        for i in id_nums:
            for u in zuser_list:
                if i == u['id']:
                    req_ref[i] = u['name']
                    break
        del id_nums

        zen_tics = []
        zen_tics_full = []
        for t in zticket_list:
            a_field = {}
            for f in t['fields']:
                if f['id'] == int(user.zen_fieldid):
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
                    
        zen_users = []
        for u in zuser_list:
            if u['id'] in req_ref:
                org_name = 'None'
                org_id = u['organization_id']
                
                if org_id is not None:
                    for o in zorg_list:
                        if o['id'] == org_id:
                            org_name = o['name']
                            break

                zen_users.append({'name': u['name'],
                            'email': u['email'],
                            'id': u['id'],
                            'org_name': org_name})
    
    if working['git']:
        git_tics = []
        on_zen = []
        for t in zen_tics_full:
            for f in t['fields']:
                if f['id'] == int(user.zen_fieldid):
                    if f['value'] is not None:
                        a_num = f['value'].split('-')
                    else:
                        a_num = ['']
                    break
            if a_num[0] == 'gh':
                on_zen.append(int(a_num[1]))

        for t in gclosed_list:
            if t['number'] in on_zen:
                git_tics.append(t)
        del on_zen

        git_tics.extend(gopen_list)
        git_tics.reverse()
        ticket_nums = [i['number'] for i in git_tics]

    if working['git'] and working['zen']:
        o_assocs = [] # open associations
        ho_assocs = [] # half-open associations
        no_assocs = [] # no associations
        working['o_assocs'] = True
        working['ho_assocs'] = True
        working['no_assocs'] = True

        for t in zen_tics_full:
            for f in t['fields']:
                if f['id'] == int(user.zen_fieldid):
                    a_num = f['value']
                    break
            a_data = {}
            a_data['z_id'] = t['id']
            a_data['z_user'] = req_ref[t['requester_id']]
            a_data['z_status'] = t['status']
            a_data['z_date'] = t['updated_at']

            if a_num is None or a_num.split('-')[0] != 'gh':
                if a_num is None or a_num == '':
                    a_data['assoc'] = 'None'
                else:
                    a_data['assoc'] = a_num
                no_assocs.append(a_data)
            
            else:
                for i in git_tics:
                    if i['number'] == int(a_num.split('-')[1]):
                        git_issue = i
                        break
                a_data['g_id'] = git_issue['number']
                a_data['g_user'] = git_issue['user']['login']
                a_data['g_labels'] = [i['name'] for i in git_issue['labels']]
                a_data['g_url'] = git_issue['html_url']
                a_data['g_status'] = git_issue['state']
                
                if a_data['g_status'] == 'open' and \
                   a_data['z_status'] == 'open':
                    a_data['g_date'] = git_issue['updated_at']
                    o_assocs.append(a_data)

                elif a_data['gstatus'] != 'open' and \
                        a_data['zstatus'] != 'open':
                    for i in range(len(git_tics)):
                        if git_tics[i]['number'] == a_data['g_id']:
                            git_tics.pop(i)
                            break
                    for i in range(len(zen_tics)):
                        if zen_tics[i]['id'] == a_data['z_id']:
                            zen_tics.pop(i)
                            break

                else:
                    if a_data['g_status'] == 'open':
                        a_data['closed'] = 'z'
                    else:
                        a_data['closed'] = 'g'
                    ho_assocs.append(a_data)
    else:
        working['o_assocs'] = False
        working['ho_assocs'] = False
        working['no_assocs'] = False
        
    return render_to_response('associations/home.html', {'git_tics': git_tics,
                                'zen_tics': zen_tics, 'zen_users': zen_users, 
                                'ho_assocs': c_assocs, 'o_assocs': o_assocs,
                                'no_assocs': no_assocs, 'repo': user.git_repo, 
                                'zen_url': user.zen_url, 'working': working},
                                context_instance=RequestContext(request))
