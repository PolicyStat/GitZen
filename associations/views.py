from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login, logout
from django import forms
from github2.client import Github
from github2.issues import *
from zendesk import Zendesk
from xml.dom import minidom
from associations.models import GZUser

class LogForm(forms.Form):
    username = forms.CharField(max_length=75)
    password = forms.CharField(max_length=75, widget=forms.PasswordInput)

class NewForm(forms.Form):
    username = forms.CharField(max_length=75)
    password = forms.CharField(max_length=75, widget=forms.PasswordInput)
    affirmpass = forms.CharField(max_length=75, widget=forms.PasswordInput)
    git_name = forms.CharField(max_length=75)
    git_repo = forms.CharField(max_length=75)
    git_key = forms.CharField(max_length=75)
    zen_name = forms.CharField(max_length=75)
    zen_pass = forms.CharField(max_length=75, widget=forms.PasswordInput)
    zen_url = forms.CharField(max_length=100)
    zen_viewid = forms.CharField(max_length=25)
    zen_fieldid = forms.CharField(max_length=50)

class ChangeForm(forms.Form):
    old_pass = forms.CharField(max_length=75, widget=forms.PasswordInput,
                                required=False)
    new_pass = forms.CharField(max_length=75, widget=forms.PasswordInput, 
                                required=False)
    aff_pass = forms.CharField(max_length=75, widget=forms.PasswordInput, 
                                required=False)
    git_name = forms.CharField(max_length=75, required=False)
    git_repo = forms.CharField(max_length=75, required=False)
    git_key = forms.CharField(max_length=75, required=False)
    zen_name = forms.CharField(max_length=75, required=False)
    zen_pass = forms.CharField(max_length=75, widget=forms.PasswordInput, 
                                required=False)
    zen_url = forms.CharField(max_length=100, required=False)
    zen_viewid = forms.CharField(max_length=25, required=False)
    zen_fieldid = forms.CharField(max_length=50, required=False)

def user_login(request):
    if request.method == 'POST':
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

        elif 'new' in request.POST:
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
                    user.git_repo = data['git_repo']
                    user.git_key = data['git_key']
                    user.zen_name = data['zen_name']
                    user.zen_pass = data['zen_pass']
                    user.zen_url = data['zen_url']
                    user.zen_viewid = data['zen_viewid']
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

def nope(request, nope_num):
    return render_to_response('associations/nope.html', 
                                {'nope_num': nope_num,})

def confirm(request, con_num):
    return render_to_response('associations/confirm.html',
                                {'con_num': con_num,})

def home(request):
    user = request.user
    gitTics = ''
    zenTics = ''

    try:
        github = Github(username=user.git_name, 
                    api_token=user.git_key)
        repo = user.git_repo
    except:
        gitTics = 'broken'

    try:
        zendesk = Zendesk(user.zen_url, user.zen_name,
                            user.zen_pass)
        zticket_list = minidom.parseString(zendesk.list_tickets \
            (view_id=user.zen_viewid)).getElementsByTagName('ticket')
        zuser_list = minidom.parseString(zendesk.list_users()). \
            getElementsByTagName('user')
    except:
        zenTics = 'broken'
        
    
    if gitTics != 'broken':
        gitTics = github.issues.list(repo, state='open')
        ticket_nums = [i.number for i in github.issues.list(repo, state='open')] \
                    + [i.number for i in github.issues.list(repo, state='closed')]
    
    if zenTics != 'broken':
        zenTics = []
        for t in zticket_list:
            zenTics.append({
                'id': t.getElementsByTagName('nice-id')[0].firstChild.data,
                'req_name':
                t.getElementsByTagName('req-name')[0].firstChild.data,
                'subject': t.getElementsByTagName('subject')[0].firstChild.data,
            })

        zenUsers = []
        for i in zuser_list:
            for o in minidom.parseString(zendesk.list_organizations()). \
            getElementsByTagName('organization'):
                org_name = 'None'
                org_id = i.getElementsByTagName('organization-id')[0].firstChild
                if org_id is not None and o.getElementsByTagName \
                ('id')[0].firstChild.data == org_id.data:
                    org_name = o.getElementsByTagName('name')[0].firstChild.data
                    break

            zenUsers.append({'name': i.getElementsByTagName('name')[0].firstChild.data,
                        'email': i.getElementsByTagName('email')[0].firstChild.data,
                        'id': i.getElementsByTagName('id')[0].firstChild.data,
                        'org_name': org_name})
    else:
        zenUsers = 'broken'
    
    if gitTics != 'broken' and zenTics != 'broken':
        c_assocs = []
        o_assocs = []
        no_assocs = []
        for i in zticket_list:
            anum = i.getElementsByTagName(user.zen_fieldid)[0].firstChild
            a_data = {}
            a_data['znum'] = \
                i.getElementsByTagName('nice-id')[0].firstChild.data
            a_data['zuser'] = \
                i.getElementsByTagName('req-name')[0].firstChild.data
            a_data['zdate'] = \
                i.getElementsByTagName('updated-at')[0].firstChild.data

            if anum is None or not anum.data.split('-')[0] == 'gh' or not \
            int(anum.data.split('-')[1]) in ticket_nums:
                if anum is None:
                    a_data['dassoc'] = 'None'
                else:
                    a_data['dassoc'] = anum.data
                no_assocs.append(a_data)
            
            elif anum.data.split('-')[0] == 'gh':
                git_issue = github.issues.show(repo, anum.data.split('-')[1])
                a_data['gnum'] = git_issue.number
                a_data['guser'] = git_issue.user
                a_data['glabels'] = git_issue.labels
                a_data['gstate'] = git_issue.state
                if git_issue.state == 'open':
                    a_data['gdate'] = git_issue.updated_at
                    o_assocs.append(a_data)
                else:
                    a_data['gdate'] = git_issue.closed_at
                    c_assocs.append(a_data)
    else:
        c_assocs = 'broken'
        o_assocs = 'broken'
        no_assocs = 'broken'
        
    return render_to_response('associations/home.html', {'gitTics': gitTics,
                                'zenTics': zenTics, 'zenUsers': zenUsers, 
                                'c_assocs': c_assocs, 'o_assocs': o_assocs,
                                'no_assocs': no_assocs, 'repo': repo,
                                'zen_viewid': user.zen_viewid, 
                                'zen_url': user.zen_url},
                                context_instance=RequestContext(request))

def change(request):
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
            if data['git_repo']:
                user.git_repo = data['git_repo']
            if data['git_key']:
                user.git_key = data['git_key']
            if data['zen_name']:
                user.zen_name = data['zen_name']
            if data['zen_pass']:
                user.zen_pass = data['zen_pass']
            if data['zen_url']:
                user.zen_url = data['zen_url']
            if data['zen_viewid']:
                user.zen_viewid = data['zen_viewid']
            if data['zen_fieldid']:
                user.zen_fieldid = data['zen_fieldid']
            user.save()

            return HttpResponseRedirect('/confirm/2')
    else:
        changeform = ChangeForm()
    
    return render_to_response('associations/change.html', 
                                {'changeform': changeform,},
                                context_instance=RequestContext(request))
