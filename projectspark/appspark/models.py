from django.contrib.auth.models import User
from django.db import models


class WorkhandCategory(models.Model):
    category = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = "Workhand Categories"

    def __str__(self):
        return self.category


class EventsCategory(models.Model):
    category = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = "Events Categories"

    def __str__(self):
        return self.category


class Workhand(models.Model):
    # Remove the invalid default="" — OneToOneField uses an integer PK, not a string.
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='', default='assets2/img/AnonymousPic.png')
    contact = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    workhand_category = models.ForeignKey(WorkhandCategory, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        cat = self.workhand_category.category if self.workhand_category else "Uncategorized"
        return f"{self.user.username} - {cat}"


class Company(models.Model):
    # Remove the invalid default="" — OneToOneField uses an integer PK, not a string.
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='', default='assets2/img/AnonymousPic.png')
    company_name = models.CharField(max_length=50, null=True, blank=True)
    contact = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return f"{self.company_name or 'Unnamed'} - {self.user.username}"


class Event(models.Model):
    event_category = models.ForeignKey(EventsCategory, on_delete=models.SET_NULL, null=True)
    event_name = models.CharField(max_length=50)
    description = models.TextField()
    # db_index on start_date and city: these are the primary filter fields in search queries.
    start_date = models.DateField(db_index=True)
    end_date = models.DateField()
    workhand_category = models.ForeignKey(WorkhandCategory, on_delete=models.SET_NULL, null=True)
    workhand_needed = models.IntegerField()
    # DecimalField prevents floating-point rounding errors on monetary values.
    payment_range = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.TextField()
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50, db_index=True)
    company_id = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        poster = self.company_id.user.first_name if self.company_id else "Unknown"
        return f"{self.event_name} (by {poster})"


class WorkhandApplications(models.Model):
    workhand = models.ForeignKey(Workhand, on_delete=models.SET_NULL, null=True)
    to_company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True)
    # db_index on status: filtered constantly in dashboard and notifications queries.
    status = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Workhand Applications"
        # DB-level guarantee: even two simultaneous requests can't create
        # duplicate applications for the same workhand+event.
        constraints = [
            models.UniqueConstraint(fields=['workhand', 'event'], name='unique_application_per_event')
        ]

    def __str__(self):
        wh = self.workhand.user.username if self.workhand else "Unknown workhand"
        ev = self.event.event_name if self.event else "Unknown event"
        status = "Approved" if self.status else "Pending"
        return f"{wh} → {ev} [{status}]"


class EventHistory(models.Model):
    event_category = models.ForeignKey(EventsCategory, on_delete=models.SET_NULL, null=True)
    event_name = models.CharField(max_length=50)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    workhand_category = models.ForeignKey(WorkhandCategory, on_delete=models.SET_NULL, null=True)
    workhand_needed = models.IntegerField()
    # DecimalField prevents floating-point rounding errors on monetary values.
    payment_range = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.TextField()
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    company_id = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)
    workhand_id = models.ForeignKey(Workhand, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Event Histories"

    def __str__(self):
        wh = self.workhand_id.user.username if self.workhand_id else "Unknown workhand"
        co = self.company_id.user.first_name if self.company_id else "Unknown company"
        return f"{self.event_name} — completed by {wh} (posted by {co})"


class Feedback(models.Model):
    feedback_title = models.CharField(max_length=40)
    feedback = models.TextField()
    date = models.DateField()
    event_id = models.ForeignKey(EventHistory, on_delete=models.SET_NULL, null=True)
    workhand_id = models.ForeignKey(Workhand, on_delete=models.SET_NULL, null=True)
    company_id = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name_plural = "Feedbacks"

    def __str__(self):
        ev = self.event_id.event_name if self.event_id else "Unknown event"
        wh = self.workhand_id.user.first_name if self.workhand_id else "Unknown workhand"
        co = self.company_id.user.first_name if self.company_id else "Unknown company"
        return f"{self.feedback_title} on {ev} to {wh} by {co}"
