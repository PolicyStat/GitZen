from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate
from django import forms
from github2.client import Github
from github2.issues import *
from zendesk import Zendesk
from xml.dom import minidom
from associations.models import GZUser

class LogForm(forms.Form):
    username = forms.CharField(max_length=75)
    password = forms.CharField(max_length=75)

class NewForm(forms.Form):
    username = forms.CharField(max_length=75)
    password = forms.CharField(max_length=75)
    affirmpass = forms.CharField(max_length=75)
    git_name = forms.CharField(max_length=75)
    git_repo = forms.CharField(max_length=75)
    git_key = forms.CharField(max_length=75)
    zen_name = forms.CharField(max_length=75)
    zen_url = forms.CharField(max_length=100)
    zen_pass = forms.CharField(max_length=75)

def login(request):
    if request.method == 'POST':
        if 'log' in request.POST:
            logform = LogForm(request.POST)
            if logform.is_valid():
                user = authenticate(
                    username=logform.cleaned_data['username'],
                    password=logform.cleaned_data['password'],
                )

                if user is not None:
                    github = Github(username=user.git_name, 
                                    api_token=user.git_key)
                    repo = user.git_repo
                    zendesk = Zendesk(user.zen_url, user.zen_name,
                                    user.zen_pass)
                    zticket_list = minidom.parseString(zendesk.list_tickets \
                        (view_id=22796456)).getElementsByTagName('ticket')
                    zuser_list = minidom.parseString(zendesk.list_users()). \
                        getElementsByTagName('user')

                    return HttpResponseRedirect('/main/')
                else:
                    return HttpResponseRedirect('/nope/1')
            newform = NewForm()

        elif 'new' in request.POST:
            newform = NewForm(request.POST)
            if newform.is_valid():
                data = newform.cleaned_data
                if data['password'] == data['affirmpass']
                    user = GZUser.objects.create_user(
                        username=data['username'],
                        password=data['password'],
                    )
                    user.git_name = data['git_name']
                    user.git_repo = data['git_repo']
                    user.git_key = data['git_key']
                    user.zen_name = data['zen_name']
                    user.zen_url = data['zen_url']
                    user.zen_pass = data['zen_pass']

                    user.save()
                    return HttpResponseRedirect('/login/')
                else:
                    return HttpResponseRedirect('/nope/2')
            logform = LogForm()
    else:
        logform = LogForm()
        newform = NewForm()

    return render_to_response('associations/login.html', {'logform': logfrom,
                                'newform': newform,}, 
                                context_instance=RequestContext(request))


def home(request):
    gitTic = github.issues.list(repo, state='open')
    ticket_nums = [i.number for i in github.issues.list(repo, state='open')] \
                + [i.number for i in github.issues.list(repo, state='closed')]

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

    c_assocs = []
    o_assocs = []
    no_assocs = []
    for i in zticket_list:
        anum = i.getElementsByTagName('field-143159')[0].firstChild
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
        
    return render_to_response('associations/home.html', {'gitTic': gitTic,
                                'zenTics':zenTics, 'zenUsers': zenUsers, 
                                'c_assocs': c_assocs, 'o_assocs': o_assocs,
                                'no_assocs': no_assocs,}, 
                                context_instance=RequestContext(request))

def git(request, git_num):
    issue = github.issues.show(repo, git_num)
    comments = github.issues.comments(repo, git_num) 
    return render_to_response('associations/git.html', {'issue':issue,
                                'comments': comments})

def zenT(request, zen_num):
    cntr = 0

    for t in zticket_list:
        if t.getElementsByTagName('nice-id')[0].firstChild.data == zen_num:
            break
        cntr += 1

    ticket_data = {}
    for i in zticket_list[cntr].childNodes:
        if i.firstChild is not None:
            if i.nodeName == 'nice-id':
                ticket_data['nice_id'] = i.firstChild.data
            else:
                ticket_data[i.nodeName] = i.firstChild.data

    return render_to_response('associations/zenT.html', 
                                {'ticket_data': ticket_data,})

def zenU(request, user_num):
    cntr = 0
    
    for u in zuser_list:
        user_id = u.getElementsByTagName('id')[0].firstChild
        if user_id is not None and user_id.data == user_num:
            break
        cntr += 1

    user_data = {}
    for i in zuser_list[cntr].childNodes:
        if i.firstChild is not None:
            user_data[i.nodeName] = i.firstChild.data

    return render_to_response('associations/zenU.html', 
                                {'user_data': user_data,})
    
