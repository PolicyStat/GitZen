from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django import forms
from github2.client import Github
from github2.issues import *
from zendesk import Zendesk
from associations.models import Association

github = Github(username='FriedRice', api_token='68c7180e60ad2354b9bc84792c6ba7ab')
repo = 'PolicyStat/PolicyStat'
zendesk = Zendesk('https://policystat.zendesk.com', 'wes@policystat.com',
                    'l2us3apitokens')

class AssocForm(forms.Form):
    gnum = forms.IntegerField()
    znum = forms.IntegerField()
    notes = forms.CharField(max_length=200)

def home(request):
    issues = github.issues.list(repo, state='open')
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
        
    if request.method == 'POST':
        form = AssocForm(request.POST)
        if form.is_valid():
            a = Association(git=form.cleaned_data['gnum'],
            zen=form.cleaned_data['znum'], notes=form.cleaned_data['notes'])
            a.save()

            return HttpResponseRedirect('/as/')
    else:
        form = AssocForm()

    return render_to_response('associations/home.html', {'issues': issues,
                                'assocs': assocs, 'opentickets': opentickets,
                                'dates': dates, 'gitLabels': gitLabels, 
                                'form':form,}, context_instance=
                                RequestContext(request))

def git(request, git_num):
    issue = github.issues.show(repo, git_num)
    comments = github.issues.comments(repo, git_num) 
    return render_to_response('associations/git.html', {'issue':issue,
                                'comments': comments})

def zen(request, zen_num):
   pass 
