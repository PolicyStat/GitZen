from django.db import models

class Association(models.Model):
    git = models.CharField(max_length=25)
    zen = models.CharField(max_length=50)
    notes = models.CharField(max_length=200)
    date = models.DateField(auto_now_add=True)
    status = models.BooleanField()
    info = models.TextField()

class GitTicket(models.Model):
    name = models.CharField(max_length=25)
    gitInfo = models.TextField()

class ZenTicket(models.Model):
    email = models.EmailField()
    zenInfo = models.TextField()
    
