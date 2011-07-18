from django.http import HttpResponse
from github2.client import Github
from github2.issues import *
from zendesk import Zendesk

github = Github(username='FriedRice', api_token='68c7180e60ad2354b9bc84792c6ba7ab')
#zendesk = Zendesk() 

def home(request):
    issues = github.issues.list('PolicyStat/PolicyStat', state='open')
    output = '<br/>'.join(['<a href="/as/git/%s/">%s.</a> %s' % (i.number, 
                        i.number, i.title) for i in issues])
    return HttpResponse(output)

def git(request, git_num):
    issue = github.issues.show('PolicyStat/PolicyStat', git_num)
    output = '<br/>'.join(['%s: %s' % (k, v) for k, v in issue])
    return HttpResponse(output)

def zen(request, zen_num):
   pass 
