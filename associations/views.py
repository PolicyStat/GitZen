from django.http import HttpResponse
from github2.client import Github
from github2.issues import *

github = Github(username='FriedRice', api_token='68c7180e60ad2354b9bc84792c6ba7ab')

def home(request):
    issues = github.issues.list('PolicyStat/PolicyStat', state='open')
    output = '<br/>'.join([str(i.number) + '. ' + i.title for i in issues])
    return HttpResponse(output)

def git(request, git_num):
    pass
