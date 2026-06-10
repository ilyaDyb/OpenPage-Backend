import logging

from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView, RetrieveAPIView, RetrieveUpdateAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api_errors import error_response
from core.books.permissions import IsReader
from core.profiles.models import AuthorProfile, AuthorSubscription, ReaderProfile
from core.profiles.serializers import (
    AuthorSubscriptionSerializer,
    AuthorProfileSerializer,
    PublicUserProfileSerializer,
    UserProfileSerializer,
)


logger = logging.getLogger(__name__)
User = get_user_model()


class CurrentUserProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.select_related('reader_profile', 'author_profile').prefetch_related(
            'reader_profile__preferred_genres'
        )

    @extend_schema(
        operation_id='profile_me_retrieve',
        summary='Current user profile',
        description='Return the authenticated user profile with nested reader and author profiles.',
        tags=['User Profiles'],
        responses={200: UserProfileSerializer, 401: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/profile/ for user %s", request.user.username)
        return super().get(request, *args, **kwargs)

    @extend_schema(
        operation_id='profile_me_update',
        summary='Replace current user profile',
        description='Replace editable fields on the authenticated user profile.',
        tags=['User Profiles'],
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer, 400: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
    )
    def put(self, request, *args, **kwargs):
        logger.info("PUT /api/profile/ for user %s", request.user.username)
        return super().put(request, *args, **kwargs)

    @extend_schema(
        operation_id='profile_me_partial_update',
        summary='Partially update current user profile',
        description='Update one or more editable fields on the authenticated user profile.',
        tags=['User Profiles'],
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer, 400: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
    )
    def patch(self, request, *args, **kwargs):
        logger.info("PATCH /api/profile/ for user %s", request.user.username)
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        return self.get_queryset().get(pk=self.request.user.pk)

    def perform_update(self, serializer):
        serializer.save()
        logger.info("Profile updated for user %s", self.request.user.username)


class PublicUserProfileView(RetrieveAPIView):
    serializer_class = PublicUserProfileSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id='profile_public_retrieve',
        summary='Public profile by id',
        description='Return the public profile for a user id.',
        tags=['User Profiles'],
        responses={200: PublicUserProfileSerializer, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/profile/%s/", kwargs.get('pk'))
        return super().get(request, *args, **kwargs)

    def get_object(self):
        queryset = User.objects.select_related('reader_profile', 'author_profile').prefetch_related(
            'reader_profile__preferred_genres'
        )
        obj = get_object_or_404(queryset, pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj


class UserByUsernameProfileView(RetrieveAPIView):
    serializer_class = PublicUserProfileSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id='profile_username_retrieve',
        summary='Public profile by username',
        description='Return the public profile for a username.',
        tags=['User Profiles'],
        responses={200: PublicUserProfileSerializer, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/profile/username/%s/", kwargs.get('username'))
        return super().get(request, *args, **kwargs)

    def get_object(self):
        queryset = User.objects.select_related('reader_profile', 'author_profile').prefetch_related(
            'reader_profile__preferred_genres'
        )
        obj = get_object_or_404(queryset, username=self.kwargs['username'])
        self.check_object_permissions(self.request, obj)
        return obj


class CreateReaderProfileView(APIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id='profile_reader_create',
        summary='Ensure reader profile',
        description='Return the authenticated user profile and create reader profile only if it is missing.',
        tags=['User Profiles'],
        request=None,
        responses={200: UserProfileSerializer, 201: UserProfileSerializer},
    )
    def post(self, request):
        logger.info("POST /api/profile/reader/ for user %s", request.user.username)
        _, created = ReaderProfile.objects.get_or_create(user=request.user)
        if created:
            logger.info("Reader profile created for user %s", request.user.username)
            return Response(UserProfileSerializer(request.user).data, status=status.HTTP_201_CREATED)
        return Response(UserProfileSerializer(request.user).data, status=status.HTTP_200_OK)


class CreateAuthorProfileView(APIView):
    serializer_class = AuthorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id='profile_author_create',
        summary='Create author profile',
        description='Create an author profile request for the authenticated user.',
        tags=['User Profiles'],
        request=AuthorProfileSerializer,
        responses={201: AuthorProfileSerializer, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        logger.info("POST /api/profile/author/ for user %s", request.user.username)

        if hasattr(request.user, 'author_profile'):
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'author_profile': ['Author profile already exists.']},
            )

        serializer = AuthorProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, requested_at=timezone.now(), is_approved=False)
        logger.info("Author profile created for user %s", request.user.username)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AuthorSubscriptionListView(ListAPIView):
    serializer_class = AuthorSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsReader]

    def get_queryset(self):
        return (
            AuthorSubscription.objects.filter(reader=self.request.user.reader_profile)
            .select_related('author__user', 'reader__user')
            .order_by('-created_at')
        )

    @extend_schema(
        operation_id='profile_author_subscription_list',
        summary='My author subscriptions',
        description='List authors followed by the current reader.',
        tags=['Author Subscriptions'],
        responses={200: AuthorSubscriptionSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/profile/author-subscriptions/ for user %s", request.user.username)
        return super().get(request, *args, **kwargs)


class AuthorSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsReader]

    @extend_schema(
        operation_id='profile_author_subscribe',
        summary='Subscribe to author',
        description='Subscribe the current reader to an approved author.',
        tags=['Author Subscriptions'],
        request=None,
        responses={200: AuthorSubscriptionSerializer, 201: AuthorSubscriptionSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def post(self, request, pk):
        logger.info("POST /api/profile/authors/%s/subscription/ for user %s", pk, request.user.username)
        author = get_object_or_404(AuthorProfile.objects.select_related('user'), pk=pk, is_approved=True)
        if author.user_id == request.user.id:
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'author': ['You cannot subscribe to yourself.']},
            )

        notify_new_books = request.data.get('notify_new_books', True)
        if isinstance(notify_new_books, str):
            notify_new_books = notify_new_books.lower() in {'1', 'true', 'yes'}

        subscription, created = AuthorSubscription.objects.get_or_create(
            reader=request.user.reader_profile,
            author=author,
            defaults={'notify_new_books': bool(notify_new_books)},
        )
        if not created and subscription.notify_new_books != bool(notify_new_books):
            subscription.notify_new_books = bool(notify_new_books)
            subscription.save(update_fields=['notify_new_books'])

        return Response(
            AuthorSubscriptionSerializer(subscription, context={'request': request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id='profile_author_unsubscribe',
        summary='Unsubscribe from author',
        description='Remove current reader subscription from an author.',
        tags=['Author Subscriptions'],
        request=None,
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def delete(self, request, pk):
        logger.info("DELETE /api/profile/authors/%s/subscription/ for user %s", pk, request.user.username)
        author = get_object_or_404(AuthorProfile, pk=pk)
        deleted_count, _ = AuthorSubscription.objects.filter(
            reader=request.user.reader_profile,
            author=author,
        ).delete()
        return Response({'subscribed': False, 'deleted': bool(deleted_count)})
