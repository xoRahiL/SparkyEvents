from django.contrib import admin
from .models import *

# Register your models here.


admin.site.register(Workhand)
admin.site.register(WorkhandCategory)
admin.site.register(WorkhandApplications)
# admin.site.register(Feed)

admin.site.register(Company)
admin.site.register(Event)
admin.site.register(EventsCategory)

admin.site.register(EventHistory)
admin.site.register(Feedback)
