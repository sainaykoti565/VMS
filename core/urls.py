from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Visitor
    path('register-visitor/', views.register_visitor, name='register_visitor'),
    path('visitors/', views.visitor_list, name='visitor_list'),
    path('visitor-history/', views.visitor_history, name='visitor_history'),

    # Check-in / Check-out
    path('check-in/<int:visit_id>/', views.check_in, name='check_in'),
    path('check-out/<int:visit_id>/', views.check_out, name='check_out'),

    # Approve / Reject
    path('approve/<int:visit_id>/', views.approve_visit, name='approve_visit'),
    path('reject/<int:visit_id>/', views.reject_visit, name='reject_visit'),

    # Admin
    path('manage-users/', views.manage_users, name='manage_users'),
    path('create-user/', views.create_user, name='create_user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),

    # Blacklist
    path('blacklist/', views.blacklist_management, name='blacklist_management'),
    path('blacklist/add/<int:visitor_id>/', views.blacklist_visitor, name='blacklist_visitor'),
    path('blacklist/remove/<int:blacklist_id>/', views.remove_blacklist, name='remove_blacklist'),

    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),

    # Reports
    path('reports/', views.reports, name='reports'),
]
