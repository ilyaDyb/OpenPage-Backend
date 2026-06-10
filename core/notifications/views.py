import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.notifications.models import Notification
from core.notifications.serializers import (
    NotificationSerializer,
    NotificationUnreadCountSerializer,
)


logger = logging.getLogger(__name__)


class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user).select_related('actor')
        unread = self.request.query_params.get('unread')
        notification_type = self.request.query_params.get('type')

        if unread is not None:
            wants_unread = unread.lower() in {'1', 'true', 'yes'}
            queryset = queryset.filter(is_read=not wants_unread)

        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        return queryset

    @extend_schema(
        operation_id='notifications_list',
        summary='List notifications',
        description='List current user notifications. Supports unread=true and type filtering.',
        tags=['Notifications'],
        parameters=[
            OpenApiParameter(name='unread', required=False, type=bool),
            OpenApiParameter(name='type', required=False, type=str),
        ],
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/notifications/ for user %s", request.user.username)
        return super().get(request, *args, **kwargs)


class NotificationUnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id='notifications_unread_count',
        summary='Unread notifications count',
        tags=['Notifications'],
        responses={200: NotificationUnreadCountSerializer},
    )
    def get(self, request):
        logger.info("GET /api/notifications/unread-count/ for user %s", request.user.username)
        return Response({'unread_count': Notification.objects.filter(recipient=request.user, is_read=False).count()})


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id='notifications_mark_read',
        summary='Mark notification as read',
        tags=['Notifications'],
        request=None,
        responses={200: NotificationSerializer, 404: OpenApiTypes.OBJECT},
    )
    def post(self, request, pk):
        logger.info("POST /api/notifications/%s/read/ for user %s", pk, request.user.username)
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.mark_as_read()
        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)


class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id='notifications_mark_all_read',
        summary='Mark all notifications as read',
        tags=['Notifications'],
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        logger.info("POST /api/notifications/read-all/ for user %s", request.user.username)
        queryset = Notification.objects.filter(recipient=request.user, is_read=False)
        updated_count = 0
        for notification in queryset:
            notification.mark_as_read()
            updated_count += 1
        return Response({'updated_count': updated_count})
