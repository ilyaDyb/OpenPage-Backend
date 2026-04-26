"""Views for bookmarks, reading history, reviews, and author requests."""
import logging

from django.db import IntegrityError, transaction
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
    get_object_or_404,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api_errors import error_response
from core.books.models import ReviewLike
from core.books.permissions import IsModeratorOrStaff, IsOwner, IsReader
from core.books.reading_serializers import (
    AuthorRequestModerationResultSerializer,
    AuthorRequestCreateSerializer,
    AuthorRequestModerationSerializer,
    AuthorRequestSerializer,
    BookmarkSerializer,
    ReadingHistorySerializer,
    ReviewLikeResponseSerializer,
    ReviewCreateSerializer,
    ReviewSerializer,
    ensure_reader_book_access,
)
from core.books.reading_api import sync_reader_books_read
from core.profiles.models import AuthorProfile, Bookmark, ReadingHistory, Review


logger = logging.getLogger(__name__)


class BookmarkListView(ListAPIView):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated, IsReader]

    def get_queryset(self):
        queryset = Bookmark.objects.filter(reader=self.request.user.reader_profile).select_related('book')
        book_id = self.request.query_params.get('book')
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        return queryset.order_by('book__title', 'page_number', 'created_at')

    @extend_schema(
        operation_id='reading_bookmark_list',
        summary='My bookmarks',
        description='List all bookmarks of the current reader, optionally filtered by book.',
        tags=['Reading Features'],
        parameters=[OpenApiParameter(name='book', required=False, type=str, description='Book ID')],
        responses={200: BookmarkSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/reading/bookmarks/ for user %s", request.user.username)
        return super().get(request, *args, **kwargs)


class BookmarkCreateView(CreateAPIView):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated, IsReader]

    @extend_schema(
        operation_id='reading_bookmark_create',
        summary='Create bookmark',
        description='Create a new bookmark for a book.',
        tags=['Reading Features'],
        request=BookmarkSerializer,
        responses={201: BookmarkSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):
        logger.info("POST /api/reading/bookmarks/create/ for user %s", request.user.username)
        return super().post(request, *args, **kwargs)


class BookmarkDeleteView(DestroyAPIView):
    queryset = Bookmark.objects.select_related('reader__user', 'book')
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    lookup_field = 'pk'

    @extend_schema(
        operation_id='reading_bookmark_delete',
        summary='Delete bookmark',
        description='Delete bookmark by ID.',
        tags=['Reading Features'],
        responses={204: None, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def delete(self, request, *args, **kwargs):
        logger.info("DELETE /api/reading/bookmarks/%s/delete/", kwargs.get('pk'))
        return super().delete(request, *args, **kwargs)


class ReadingHistoryListView(ListAPIView):
    serializer_class = ReadingHistorySerializer
    permission_classes = [permissions.IsAuthenticated, IsReader]

    def get_queryset(self):
        return ReadingHistory.objects.filter(reader=self.request.user.reader_profile).select_related('book')

    @extend_schema(
        operation_id='reading_history_list',
        summary='Reading history',
        description='List reading history with progress of the current reader.',
        tags=['Reading Features'],
        responses={200: ReadingHistorySerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/reading/reading-history/ for user %s", request.user.username)
        return super().get(request, *args, **kwargs)


class ReadingHistoryCreateView(CreateAPIView):
    serializer_class = ReadingHistorySerializer
    permission_classes = [permissions.IsAuthenticated, IsReader]

    @extend_schema(
        operation_id='reading_history_create',
        summary='Start reading',
        description='Create reading history for a new book, or return the existing history for it.',
        tags=['Reading Features'],
        request=ReadingHistorySerializer,
        responses={200: ReadingHistorySerializer, 201: ReadingHistorySerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):
        logger.info("POST /api/reading/reading-history/create/ for user %s", request.user.username)
        context = self.get_serializer_context()
        context['allow_existing_history'] = True
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)

        book = serializer.validated_data['book']
        reader_profile = request.user.reader_profile
        last_page_read = serializer.validated_data.get('last_page_read', 0)

        try:
            with transaction.atomic():
                history, created = ReadingHistory.objects.get_or_create(
                    reader=reader_profile,
                    book=book,
                    defaults={'last_page_read': last_page_read},
                )
        except IntegrityError:
            history = ReadingHistory.objects.get(reader=reader_profile, book=book)
            created = False

        if created and last_page_read:
            total_pages = history.book.pages if history.book and history.book.pages > 0 else 1
            history.update_progress(last_page_read, total_pages)

        sync_reader_books_read(history.reader)
        output = self.get_serializer(history)
        headers = self.get_success_headers(output.data) if created else {}
        return Response(output.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK, headers=headers)


class ReadingHistoryUpdateView(UpdateAPIView):
    queryset = ReadingHistory.objects.select_related('reader__user', 'book')
    serializer_class = ReadingHistorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    lookup_field = 'pk'

    @extend_schema(
        operation_id='reading_history_update',
        summary='Update reading progress',
        description='Update reading progress for an existing history record.',
        tags=['Reading Features'],
        request=ReadingHistorySerializer,
        responses={200: ReadingHistorySerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def patch(self, request, *args, **kwargs):
        logger.info("PATCH /api/reading/reading-history/%s/update/", kwargs.get('pk'))
        return super().patch(request, *args, **kwargs)

    def perform_update(self, serializer):
        history = serializer.save()
        sync_reader_books_read(history.reader)


class ReviewListView(ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Review.objects.select_related('reader__user', 'book').prefetch_related('likes').order_by('-created_at')
        book_id = self.request.query_params.get('book')
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        return queryset

    @extend_schema(
        operation_id='reading_review_list',
        summary='List reviews',
        description='List all reviews or filter them by book.',
        tags=['Reading Features'],
        parameters=[OpenApiParameter(name='book', required=False, type=str, description='Book ID')],
        responses={200: ReviewSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/reading/reviews/")
        return super().get(request, *args, **kwargs)


class ReviewCreateView(CreateAPIView):
    serializer_class = ReviewCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsReader]

    @extend_schema(
        operation_id='reading_review_create',
        summary='Create review',
        description='Create a new review for a book.',
        tags=['Reading Features'],
        request=ReviewCreateSerializer,
        responses={201: ReviewSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):
        logger.info("POST /api/reading/reviews/create/ for user %s", request.user.username)
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        output = ReviewSerializer(review, context=self.get_serializer_context())
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)


class ReviewDetailView(RetrieveAPIView):
    queryset = Review.objects.select_related('reader__user', 'book').prefetch_related('likes')
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    @extend_schema(
        operation_id='reading_review_retrieve',
        summary='Review details',
        description='Get full review details.',
        tags=['Reading Features'],
        responses={200: ReviewSerializer, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/reading/reviews/%s/", kwargs.get('pk'))
        return super().get(request, *args, **kwargs)


class ReviewLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsReader]

    @extend_schema(
        operation_id='reading_review_like',
        summary='Like review',
        description='Create a like for a review or return the current liked state.',
        tags=['Reading Features'],
        request=None,
        responses={200: ReviewLikeResponseSerializer, 201: ReviewLikeResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def post(self, request, pk):
        logger.info("POST /api/reading/reviews/%s/like/ by user %s", pk, request.user.username)
        review = get_review_for_like(request, pk)
        _, created = ReviewLike.objects.get_or_create(reader=request.user.reader_profile, review=review)
        likes_count = sync_review_likes_count(review)
        return Response(
            {
                'success': True,
                'liked': True,
                'likes_count': likes_count,
                'helpful_count': likes_count,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id='reading_review_unlike',
        summary='Unlike review',
        description='Delete the current reader like from a review.',
        tags=['Reading Features'],
        request=None,
        responses={200: ReviewLikeResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def delete(self, request, pk):
        logger.info("DELETE /api/reading/reviews/%s/like/ by user %s", pk, request.user.username)
        review = get_review_for_like(request, pk)
        ReviewLike.objects.filter(reader=request.user.reader_profile, review=review).delete()
        likes_count = sync_review_likes_count(review)
        return Response(
            {
                'success': True,
                'liked': False,
                'likes_count': likes_count,
                'helpful_count': likes_count,
            }
        )


class ReviewHelpfulView(ReviewLikeView):
    permission_classes = [permissions.IsAuthenticated, IsReader]

    @extend_schema(
        operation_id='reading_review_helpful',
        summary='Mark review as helpful',
        description='Legacy alias for review like.',
        tags=['Reading Features'],
        request=None,
        responses={200: ReviewLikeResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def post(self, request, pk):
        logger.info("POST /api/reading/reviews/%s/helpful/ by user %s", pk, request.user.username)
        response = super().post(request, pk)
        response.status_code = status.HTTP_200_OK
        return response


class ReviewDeleteView(DestroyAPIView):
    queryset = Review.objects.select_related('reader__user', 'book')
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    lookup_field = 'pk'

    @extend_schema(
        operation_id='reading_review_delete',
        summary='Delete review',
        description='Delete your own review.',
        tags=['Reading Features'],
        responses={204: None, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def delete(self, request, *args, **kwargs):
        logger.info("DELETE /api/reading/reviews/%s/delete/", kwargs.get('pk'))
        return super().delete(request, *args, **kwargs)

    def perform_destroy(self, instance):
        reader = instance.reader
        super().perform_destroy(instance)
        reader.reviews_written = Review.objects.filter(reader=reader).count()
        reader.save(update_fields=['reviews_written'])


class AuthorRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id='reading_author_request_create',
        summary='Request author status',
        description='Create an author profile request for moderation.',
        tags=['Author Management'],
        request=AuthorRequestCreateSerializer,
        responses={201: AuthorRequestSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        logger.info("POST /api/reading/author/request/ for user %s", request.user.username)

        if hasattr(request.user, 'author_profile'):
            author_profile = request.user.author_profile
            if author_profile.is_approved:
                return error_response(
                    error_type='validation_error',
                    detail='Validation failed.',
                    status_code=status.HTTP_400_BAD_REQUEST,
                    errors={'author_profile': ['You already have an approved author profile.']},
                )

            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'author_profile': ['Your author request is already pending moderation.']},
                extra={'requested_at': author_profile.requested_at},
            )

        serializer = AuthorRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        author_profile = serializer.save(
            user=request.user,
            is_approved=False,
            requested_at=timezone.now(),
        )

        return Response(
            AuthorRequestSerializer(author_profile).data,
            status=status.HTTP_201_CREATED,
        )


class AuthorRequestsListView(ListAPIView):
    serializer_class = AuthorRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsModeratorOrStaff]

    def get_queryset(self):
        return AuthorProfile.objects.filter(is_approved=False).select_related('user').order_by('requested_at')

    @extend_schema(
        operation_id='reading_author_request_list',
        summary='List author requests',
        description='List pending author requests for moderators and staff.',
        tags=['Author Management'],
        responses={200: AuthorRequestSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/reading/author/requests/")
        return super().get(request, *args, **kwargs)


class AuthorRequestModerateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsModeratorOrStaff]

    @extend_schema(
        operation_id='reading_author_request_moderate',
        summary='Moderate author request',
        description='Approve or reject an author request.',
        tags=['Author Management'],
        request=AuthorRequestModerationSerializer,
        responses={200: AuthorRequestModerationResultSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def patch(self, request, pk):
        logger.info("PATCH /api/reading/author/requests/%s/moderate/", pk)
        serializer = AuthorRequestModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        author_profile = get_object_or_404(AuthorProfile, pk=pk)
        approve = serializer.validated_data['approve']
        rejection_reason = serializer.validated_data.get('rejection_reason', '')

        if approve:
            author_profile.is_approved = True
            author_profile.approved_at = timezone.now()
            author_profile.save(update_fields=['is_approved', 'approved_at'])

            user = author_profile.user
            user.is_author = True
            if getattr(user, 'role', 'reader') == 'reader':
                user.role = 'author'
            user.save(update_fields=['is_author', 'role'])

            return Response(
                {
                    'message': 'Author request approved.',
                    'approved_at': author_profile.approved_at,
                    'author_profile_id': str(author_profile.pk),
                }
            )

        author_profile.delete()
        return Response(
            {
                'message': 'Author request rejected.',
                'reason': rejection_reason,
            }
        )


def get_review_for_like(request, pk):
    review = get_object_or_404(Review.objects.select_related('book', 'reader__user').prefetch_related('likes'), pk=pk)
    ensure_reader_book_access(request.user, review.book, require_read_access=False)
    return review


def sync_review_likes_count(review):
    likes_count = ReviewLike.objects.filter(review=review).count()
    if review.helpful_count != likes_count:
        review.helpful_count = likes_count
        review.save(update_fields=['helpful_count'])
    return likes_count
