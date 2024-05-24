from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),

    # WORKHAND LOGIN SIDE
    path('workhandregister/', views.workhand_register, name='workhandregister'),
    path('workhandlogin/', views.workhand_login, name='workhandlogin'),
    path('workhandlogout/', views.workhand_logout, name='workhandlogout'),
    path('workhandforget/', views.workhand_forget, name='workhandforget'),

    # WORKHAND DASHBOARD SIDE
    path('workhanddashboard/', views.workhand_dashboard, name='workhanddashboard'),
    path('workhandprofile/', views.workhand_profile, name='workhandprofile'),
    path('searchevents/', views.search_events, name='searchevents'),
    path('applyforevent/<int:id>/', views.apply_for_event, name='applyforevent'),
    path('approved/', views.approved, name='approved'),
    path('eventcompleted/<int:id>/', views.event_completed, name='eventcompleted'),

    # COMPANY LOGIN SIDE
    path('companyregister/', views.company_register, name='companyregister'),
    path('companylogin/', views.company_login, name='companylogin'),
    path('companylogout/', views.company_logout, name='companylogout'),
    path('companyforget/', views.company_forget, name='companyforget'),

    # COMPANY DASHBOARD SIDE
    path('companydashboard/', views.company_dashboard, name='companydashboard'),
    path('postevent/', views.post_event, name='postevent'),
    path('companyprofile/', views.company_profile, name='companyprofile'),
    path('manageevent/', views.manage_event, name='manageevent'),
    path('updateevent/<int:id>/', views.update_event, name='updateevent'),
    path('deleteevent/<int:id>/', views.delete_event, name='deleteevent'),
    path('approveapplications/', views.approve_applications, name='approveapplications'),
    path('approveapp/<int:id>/', views.approve_app, name='approveapp'),
    path('rejectapp/<int:id>/', views.reject_app, name='rejectapp'),
    path('workhanddetails/<int:id>/', views.workhand_details, name='workhanddetails'),

    path('workhandeventhistory/', views.workhand_event_history, name='workhandeventhistory'),
    path('companyeventhistory/', views.company_event_history, name='companyeventhistory'),

    path('workhandfeedback/<int:eid>/', views.workhand_feedback, name='workhandfeedback'),
    path('companyfeedback/<int:id>/', views.company_feedback, name='companyfeedback'),

]
