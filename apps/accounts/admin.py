from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'is_active', 'is_staff', 'date_joined', 'storage_used_display']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['email', 'username']
    ordering = ['-date_joined']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Storage', {'fields': ('storage_quota', 'storage_used')}),
        ('Settings', {'fields': ('profile_photo', 'email_notifications')}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Profile', {'fields': ('email', 'profile_photo')}),
    )
