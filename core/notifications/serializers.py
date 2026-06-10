from rest_framework import serializers

from core.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='notification_type', read_only=True)
    actor_name = serializers.CharField(source='actor.username', read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'type',
            'title',
            'message',
            'payload',
            'actor',
            'actor_name',
            'is_read',
            'read_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
        ref_name = 'Notification'


class NotificationUnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()
