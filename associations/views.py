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

class AssocForm(forms.Form):
    gnum = forms.IntegerField()
    znum = forms.IntegerField()
    notes = forms.CharField(max_length=200)

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

    zenTic = []
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

        zenTic.append({'name': i.getElementsByTagName('name')[0].firstChild.data,  
                    'email': i.getElementsByTagName('email')[0].firstChild.data,
                    'id': i.getElementsByTagName('id')[0].firstChild.data,
                    'org_name': org_name})
        
    if request.method == 'POST':
        form = AssocForm(request.POST)
        if form.is_valid():
            a = Association(git=form.cleaned_data['gnum'],
            zen=form.cleaned_data['znum'], notes=form.cleaned_data['notes'])
            a.save()

            return HttpResponseRedirect('/as/')
    else:
        form = AssocForm()

    return render_to_response('associations/home.html', {'gitTic': gitTic,
                                'zenTic': zenTic, 'assocs': assocs, 
                                'opentickets': opentickets, 'dates': dates, 
                                'gitLabels': gitLabels, 'form':form,}, 
                                context_instance=RequestContext(request))

def git(request, git_num):
    issue = github.issues.show(repo, git_num)
    comments = github.issues.comments(repo, git_num) 
    return render_to_response('associations/git.html', {'issue':issue,
                                'comments': comments})

def zenU(request, user_num):
    cntr = 0
    user_list =  minidom.parseString(zendesk.list_users()). \
    getElementsByTagName('user')
    for i in user_list:
        user_id = i.getElementsByTagName('id')[0].firstChild
        if user_id is not None and user_id.data == user_num:
            break
        cntr += 1

    user_data = {}
    for i in user_list[cntr].childNodes:
        if i.firstChild is not None:
            user_data[i.nodeName] = i.firstChild.data

    return render_to_response('associations/zenU.html', 
                                {'user_data': user_data,})
    
