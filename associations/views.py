from django.http import HttpResponse
from github2.client import Github
from github2.issues import *
from zendesk import Zendesk

github = Github(username='FriedRice', api_token='68c7180e60ad2354b9bc84792c6ba7ab')
repo = 'PolicyStat/PolicyStat'
zendesk = Zendesk('https://policystat.zendesk.com', '', '') 

def home(request):
    issues = github.issues.list(repo, state='open')
    output = '<br/>'.join(['<a href="/as/git/%s/">%s.</a> %s' % (i.number, 
                        i.number, i.title) for i in issues])
    return HttpResponse(output)

def git(request, git_num):
    issue = github.issues.show(repo, git_num)
    comments = github.issues.comments(repo, git_num)
    output = '%s<br/><br/>Comments:<br/><br/>%s' % ('<br/>'.join(['%s: %s' % 
                (k, v) for k, v in issue]), '<br/><br/>'.join(['%s at %s:<br/>%s' % 
                (c.user, c.created_at, c.body) for c in comments]))
    
    return HttpResponse(output)

def zen(request, zen_num):
   pass 
