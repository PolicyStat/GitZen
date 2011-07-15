from django.db import models

class Association(models.Model):
    notes = models.CharField(max_length=200)
    date = models.DateField(auto_now_add=True)
    status = models.BooleanField()

class GitTicket(models.Model):
    number = models.IntegerField(primary_key=True)
    gitType = models.CharField(max_length=20)
    desc = models.TextField()

class ZenTicket(models.Model):
    incident = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=40)
    email = models.EmailField()
    zenType = models.CharField(max_length=20)
    priority = models.CharField(max_length=20)
    desc = models.TextField()
