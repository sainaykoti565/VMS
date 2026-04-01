from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Visitor, Visit, Notification, Blacklist


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'department']
    list_filter = ['role', 'department']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('VMS Info', {'fields': ('role', 'phone', 'department')}),
    )


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'company', 'created_by', 'created_at']
    search_fields = ['name', 'phone', 'email', 'company']


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ['visitor', 'host', 'purpose', 'status', 'check_in', 'check_out']
    list_filter = ['status', 'check_in']
    search_fields = ['visitor__name', 'host__username']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'is_read', 'created_at']
    list_filter = ['is_read']


@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    list_display = ['visitor', 'reason', 'blacklisted_by', 'created_at']
