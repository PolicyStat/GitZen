from django.db import models

class GitTicket(models.Model):
    number = models.IntegerField(primary_key=True)
    gitType = models.CharField(max_length=20)
    desc = models.TextField()

    def __unicode__(self):
        return str(self.number)


class ZenTicket(models.Model):
    incident = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=40)
    email = models.EmailField()
    zenType = models.CharField(max_length=20)
    priority = models.CharField(max_length=20)
    desc = models.TextField()

    def __unicode__(self):
        return str(self.incident)


class Association(models.Model):
    git = models.ForeignKey(GitTicket)
    zen = models.ForeignKey(ZenTicket)
    notes = models.CharField(max_length=200)
    date = models.DateField(auto_now_add=True)
    status = models.BooleanField()

    def __unicode__(self):
        return 'Z' + str(self.zen.incident) + '->G' + str(self.git.number)
