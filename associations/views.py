from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import render_to_response
from github2.client import Github
from github2.issues import *
from zendesk import Zendesk

github = Github(username='FriedRice', api_token='68c7180e60ad2354b9bc84792c6ba7ab')
repo = 'PolicyStat/PolicyStat'
zendesk = Zendesk('https://policystat.zendesk.com', '', '') 

def home(request):
    issues = github.issues.list(repo, state='open')
    return render_to_response('associations/home.html', {'issues': issues})

def git(request, git_num):
    issue = github.issues.show(repo, git_num)
    comments = github.issues.comments(repo, git_num) 
    return render_to_response('associations/git.html', {'issue':issue,
                                'comments': comments})

def zen(request, zen_num):
   pass 
