from django.contrib import admin
from .models import (
    Workhand, WorkhandCategory, Company, Event, EventsCategory,
    WorkhandApplications, EventHistory, Feedback,
)


@admin.register(WorkhandCategory)
class WorkhandCategoryAdmin(admin.ModelAdmin):
    list_display = ('category',)
    search_fields = ('category',)


@admin.register(EventsCategory)
class EventsCategoryAdmin(admin.ModelAdmin):
    list_display = ('category',)
    search_fields = ('category',)


@admin.register(Workhand)
class WorkhandAdmin(admin.ModelAdmin):
    list_display = ('user', 'workhand_category', 'city', 'state', 'created_at')
    list_filter = ('workhand_category', 'state')
    search_fields = ('user__username', 'user__email', 'city')
    raw_id_fields = ('user',)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'city', 'state', 'created_at')
    list_filter = ('state',)
    search_fields = ('company_name', 'user__username', 'user__email', 'city')
    raw_id_fields = ('user',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'event_category', 'company_id', 'start_date', 'end_date', 'payment_range', 'city')
    list_filter = ('event_category', 'workhand_category', 'state')
    search_fields = ('event_name', 'city', 'company_id__company_name')
    date_hierarchy = 'start_date'
    raw_id_fields = ('company_id',)


@admin.register(WorkhandApplications)
class WorkhandApplicationsAdmin(admin.ModelAdmin):
    list_display = ('workhand', 'event', 'to_company', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('workhand__user__username', 'event__event_name')
    raw_id_fields = ('workhand', 'event', 'to_company')


@admin.register(EventHistory)
class EventHistoryAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'company_id', 'workhand_id', 'payment_range', 'start_date', 'end_date', 'created_at')
    list_filter = ('event_category',)
    search_fields = ('event_name', 'company_id__company_name', 'workhand_id__user__username')
    date_hierarchy = 'start_date'


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('feedback_title', 'event_id', 'workhand_id', 'company_id', 'date')
    list_filter = ('date',)
    search_fields = ('feedback_title', 'feedback')
