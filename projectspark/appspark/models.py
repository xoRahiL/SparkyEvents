from django.contrib.auth.models import User
from django.db import models


# Create your models here.

class WorkhandCategory(models.Model):
    category = models.CharField(max_length=50)

    def __str__(self):
        return self.category


class EventsCategory(models.Model):
    category = models.CharField(max_length=50)

    def __str__(self):
        return self.category


class Workhand(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default="")
    profile_pic = models.ImageField(upload_to='media', default='assets2/img/AnonymousPic.png')
    contact = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    workhand_category = models.ForeignKey(WorkhandCategory, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.user.username + "  -" + self.workhand_category.category + "-"


class Company(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default="")
    profile_pic = models.ImageField(upload_to='media', default='assets2/img/AnonymousPic.png')
    company_name = models.CharField(max_length=50, null=True, blank=True)
    contact = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.company_name + "  -" + self.user.username + "-"


class Event(models.Model):
    event_category = models.ForeignKey(EventsCategory, on_delete=models.SET_NULL, null=True)
    event_name = models.CharField(max_length=50)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    workhand_category = models.ForeignKey(WorkhandCategory, on_delete=models.SET_NULL, null=True)
    workhand_needed = models.IntegerField()
    payment_range = models.FloatField()
    address = models.TextField()
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    company_id = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.company_id.user.first_name + " posted  -" + self.event_name + "-"


class WorkhandApplications(models.Model):
    workhand = models.ForeignKey(Workhand, on_delete=models.SET_NULL, null=True)
    to_company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True)
    status = models.BooleanField(default=False)

    # def __str__(self):
    #     s = self.status
    #     if s is True:
    #         status = "Approved"
    #     else:
    #         status = "Pending"
    #     return "Applied by " + self.workhand.user.username + " to " + self.to_company.user.first_name + " on " + self.event.event_name + " event and Status - " + status


class EventHistory(models.Model):
    event_category = models.ForeignKey(EventsCategory, on_delete=models.SET_NULL, null=True)
    event_name = models.CharField(max_length=50)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    workhand_category = models.ForeignKey(WorkhandCategory, on_delete=models.SET_NULL, null=True)
    workhand_needed = models.IntegerField()
    payment_range = models.FloatField()
    address = models.TextField()
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    company_id = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)
    workhand_id = models.ForeignKey(Workhand, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.event_name + " event completed by " + self.workhand_id.user.username + " posted by " + self.company_id.user.first_name


class Feedback(models.Model):
    feedback_title = models.CharField(max_length=40)
    feedback = models.TextField()
    date = models.DateField()
    event_id = models.ForeignKey(EventHistory, on_delete=models.SET_NULL, null=True)
    workhand_id = models.ForeignKey(Workhand, on_delete=models.SET_NULL, null=True)
    company_id = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.feedback_title + " on " + self.event_id.event_name + " to " + self.workhand_id.user.first_name + " by " + self.company_id.user.first_name
