from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django import forms
from github2.client import Github
from github2.issues import *
from zendesk import Zendesk
from xml.dom import minidom
from associations.models import Association

github = Github(username='FriedRice', api_token='68c7180e60ad2354b9bc84792c6ba7ab')
repo = 'PolicyStat/PolicyStat'
zendesk = Zendesk('https://policystat.zendesk.com', 'wes@policystat.com', 'l2us3apitokens')

class AssocTicketForm(forms.Form):
    gnum = forms.IntegerField()
    znum = forms.IntegerField()
    notes = forms.CharField(max_length=200)

class AssocUserForm(forms.Form):
    gnum = forms.IntegerField()
    zuser = forms.CharField(max_length=200)
    notes = forms.CharField(max_length=200)

class CloseForm(forms.Form):
    query = forms.CharField(max_length=1000)
    comment = forms.CharField(max_length=1000)

def home(request):
    gitTic = github.issues.list(repo, state='open')
    assocs = Association.objects.all().order_by('git')
    opentickets = [i.number for i in github.issues.list(repo, state='open')]

    dates = {}
    gitLabels = {}
    for i in github.issues.list(repo, state='open'):
        dates[i.number] = i.updated_at
        gitLabels[i.number] = i.labels
    for i in github.issues.list(repo, state='closed'):
        dates[i.number] = i.closed_at
        gitLabels[i.number] = i.labels

    zenTics = []
    for t in minidom.parseString(zendesk.list_tickets(view_id=22796456)). \
    getElementsByTagName('ticket'):
        zenTics.append({
            'id': t.getElementsByTagName('nice-id')[0].firstChild.data,
            'req_name':
            t.getElementsByTagName('req-name')[0].firstChild.data,
            'subject': t.getElementsByTagName('subject')[0].firstChild.data,
        })

    zenUsers = []
    for i in minidom.parseString(zendesk.list_users()). \
    getElementsByTagName('user'):
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
        
    if request.method == 'POST':
        if 'close' in request.POST:
            cform = CloseForm(request.POST)
            if cform.is_valid():
                query = []
                for s in cform.cleaned_data['query'].split(')'):
                    query.append(s[1:].split("|"))
                    Association

        elif 'ticket' in request.POST:
            tform = AssocTicketForm(request.POST)
            if tform.is_valid():
                a = Association(git=form.cleaned_data['gnum'],
                zen=form.cleaned_data['znum'], notes=form.cleaned_data['notes'],
                status=True)
                a.save()

                return HttpResponseRedirect('/as/')

        elif 'user' in request.POST:
            uform = AssocUserForm(request.POST)
            if uform.is_valid():
                pass
    else:
        cform = CloseForm()
        tform = AssocTicketForm()
        uform = AssocUserForm()

    return render_to_response('associations/home.html', {'gitTic': gitTic,
                                'zenTics':zenTics, 'zenUsers': zenUsers, 
                                'assocs': assocs, 'opentickets': opentickets, 
                                'dates': dates, 'gitLabels': gitLabels, 
                                'cform': cform, 'tform': tform, 
                                'uform': uform}, 
                                context_instance=RequestContext(request))

def git(request, git_num):
    issue = github.issues.show(repo, git_num)
    comments = github.issues.comments(repo, git_num) 
    return render_to_response('associations/git.html', {'issue':issue,
                                'comments': comments})

def zenT(request, zen_num):
    cntr = 0
    ticket_list = minidom.parseString( \
    zendesk.list_tickets(view_id=22796456)).getElementsByTagName('ticket')

    for t in ticket_list:
        if t.getElementsByTagName('nice-id')[0].firstChild.data == zen_num:
            break
        cntr += 1

    ticket_data = {}
    for i in ticket_list[cntr].childNodes:
        if i.firstChild is not None:
            if i.nodeName == 'nice-id':
                ticket_data['nice_id'] = i.firstChild.data
            else:
                ticket_data[i.nodeName] = i.firstChild.data

    return render_to_response('associations/zenT.html', 
                                {'ticket_data': ticket_data,})

def zenU(request, user_num):
    cntr = 0
    user_list =  minidom.parseString(zendesk.list_users()). \
    getElementsByTagName('user')

    for u in user_list:
        user_id = u.getElementsByTagName('id')[0].firstChild
        if user_id is not None and user_id.data == user_num:
            break
        cntr += 1

    user_data = {}
    for i in user_list[cntr].childNodes:
        if i.firstChild is not None:
            user_data[i.nodeName] = i.firstChild.data

    return render_to_response('associations/zenU.html', 
                                {'user_data': user_data,})
    
