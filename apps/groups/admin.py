from django.contrib import admin

from .models import Group, GroupMembership


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'privacy', 'is_archived', 'member_count', 'storage_used_display', 'created_at']
    list_filter = ['privacy', 'is_archived']
    search_fields = ['name', 'owner__username', 'owner__email']
    readonly_fields = ['storage_used', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'role', 'is_active', 'joined_at']
    list_filter = ['role', 'is_active']
    search_fields = ['user__username', 'group__name']
    ordering = ['-joined_at']
