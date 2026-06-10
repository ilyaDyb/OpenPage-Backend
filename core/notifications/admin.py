from django.contrib import admin

from core.notifications.models import Notification, NotificationEvent


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'event_key', 'status', 'attempts', 'process_after', 'processed_at', 'created_at')
    list_filter = ('event_type', 'status', 'created_at', 'processed_at')
    search_fields = ('event_key', 'last_error')
    readonly_fields = ('id', 'created_at', 'updated_at', 'processed_at')
    date_hierarchy = 'created_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'actor', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at', 'read_at')
    search_fields = ('title', 'message', 'recipient__username', 'actor__username', 'dedupe_key')
    raw_id_fields = ('recipient', 'actor')
    readonly_fields = ('id', 'created_at', 'updated_at', 'read_at')
    date_hierarchy = 'created_at'
