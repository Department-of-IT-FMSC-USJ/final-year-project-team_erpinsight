from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Auth
    path('login/',             views.login_view,            name='login'),
    path('logout/',            views.logout_view,           name='logout'),
    path('redirect/',          views.redirect_after_login,  name='redirect'),
    path('change-password/',   views.change_password_view,  name='change_password'),

    # Signup
    path('signup/admin/',      views.admin_signup_view,     name='admin_signup'),
    path('signup/employee/',   views.employee_signup_view,  name='employee_signup'),

    # Dashboards
    path('dashboard/super-admin/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('company/register/', views.register_company, name='register_company'),
    path('dashboard/admin/',       views.admin_dashboard,       name='admin_dashboard'),
    path('dashboard/employee/',    views.employee_dashboard,    name='employee_dashboard'),

    #business process
    path('processes/',              views.business_processes,       name='business_processes'),
    path('processes/add/',          views.add_business_process,     name='add_business_process'),
    path('processes/edit/<int:pk>/', views.edit_business_process,   name='edit_business_process'),
    path('processes/delete/<int:pk>/', views.delete_business_process, name='delete_business_process'),

    #employee cretion by manager
    path('employees/',                    views.employees,              name='employees'),
    path('employees/add/',                views.add_employee,           name='add_employee'),
    path('employees/delete/<int:pk>/',    views.delete_employee,        name='delete_employee'),
    path('invite/<uuid:token>/',          views.employee_invite_signup, name='employee_invite_signup'),

    #question creation
    path('questions/',                      views.evaluation_questions,   name='evaluation_questions'),
    path('questions/toggle/<int:pk>/',      views.toggle_question,        name='toggle_question'),
    path('questions/add-custom/',           views.add_custom_question,    name='add_custom_question'),
    path('questions/delete/<int:pk>/',      views.delete_custom_question, name='delete_custom_question'),
    
    #evaluvation
    path('evaluation/',          views.employee_evaluation,  name='employee_evaluation'),
    path('evaluation/submitted/', views.evaluation_submitted, name='evaluation_submitted'),

    #scoring calculation
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),

    #report generation
    path('reports/download/', views.download_report, name='download_report'),

    #comapny settings
    path('company/settings/', views.company_settings, name='company_settings'),
    path('company/edit/',     views.edit_company,     name='edit_company'),
    path('company/delete/',   views.delete_company,   name='delete_company'),

    #superadmin analytics
    path('super-admin/analytics/', views.super_admin_analytics, name='super_admin_analytics'),
]


