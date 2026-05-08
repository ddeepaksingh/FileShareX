from django.contrib import admin
from .models import AnonymousUploader, IPGroup


@admin.register(IPGroup)
class IPGroupAdmin(admin.ModelAdmin):
    list_display  = [
        'ip_address', 'used_display', 'quota_display',
        'storage_pct', 'is_active', 'is_blocked',
        'upload_count_today', 'last_activity',
    ]
    list_filter   = ['is_active', 'is_blocked']
    search_fields = ['ip_address']
    readonly_fields = [
        'id', 'storage_used', 'upload_count_today',
        'last_upload', 'created_at', 'last_activity',
    ]
    actions = ['action_block', 'action_unblock', 'action_reset_storage']

    @admin.display(description='Used')
    def used_display(self, obj):
        return obj.human_used()

    @admin.display(description='Quota')
    def quota_display(self, obj):
        return obj.human_quota()

    @admin.display(description='%')
    def storage_pct(self, obj):
        return f"{obj.storage_used_percent()}%"

    @admin.action(description='Block selected IPs')
    def action_block(self, request, qs):
        n = qs.update(is_blocked=True, is_active=False)
        self.message_user(request, f'{n} IP(s) blocked.')

    @admin.action(description='Unblock selected IPs')
    def action_unblock(self, request, qs):
        n = qs.update(is_blocked=False, is_active=True)
        self.message_user(request, f'{n} IP(s) unblocked.')

    @admin.action(description='Reset storage counter')
    def action_reset_storage(self, request, qs):
        n = qs.update(storage_used=0)
        self.message_user(request, f'{n} counter(s) reset.')


@admin.register(AnonymousUploader)
class AnonymousUploaderAdmin(admin.ModelAdmin):
    list_display  = ['cookie_short', 'ip_group', 'ua_short', 'created_at', 'last_seen']
    list_filter   = ['ip_group']
    readonly_fields = ['id', 'cookie_id', 'created_at', 'last_seen']
    raw_id_fields = ['ip_group']

    @admin.display(description='Cookie')
    def cookie_short(self, obj):
        return obj.cookie_id[:16] + '…'

    @admin.display(description='User Agent')
    def ua_short(self, obj):
        ua = obj.user_agent
        return ua[:60] + '…' if len(ua) > 60 else ua
