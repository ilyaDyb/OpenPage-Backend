"""API for reading and downloading books."""
import logging

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from core.books.permissions import IsReader, is_moderator_or_staff
from core.books.reading_serializers import ReadingHistorySerializer
from core.books.serializers import BookDetailSerializer
from core.books.models import Book
from core.profiles.models import ReadingHistory


logger = logging.getLogger(__name__)


class BookReadView(RetrieveAPIView):
    queryset = Book.objects.prefetch_related('authors', 'genres').all()
    serializer_class = BookDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsReader]
    lookup_field = 'slug'

    @extend_schema(
        summary='Read book',
        description='Return book data for reading and create reading history if needed.',
        tags=['Book Reading'],
        responses={200: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        logger.info("GET /api/reading/books/%s/read/ for user %s", slug, request.user.username)

        book = self.get_object()
        if not can_user_read_book(request.user, book):
            return Response({'detail': 'You do not have access to read this book.'}, status=status.HTTP_403_FORBIDDEN)

        book.update_views()
        history, _ = ReadingHistory.objects.get_or_create(
            reader=request.user.reader_profile,
            book=book,
        )

        return Response(
            {
                'book': self.get_serializer(book).data,
                'reading_history': ReadingHistorySerializer(history, context={'request': request}).data,
            }
        )


class BookDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsReader]

    @extend_schema(
        summary='Download book',
        description='Download the file of a book if downloading is allowed.',
        tags=['Book Reading'],
        responses={200: OpenApiTypes.BINARY, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, slug):
        logger.info("GET /api/reading/books/%s/download/ for user %s", slug, request.user.username)
        book = get_object_or_404(Book, slug=slug)

        if not can_user_download_book(request.user, book):
            return Response({'detail': 'You do not have access to download this book.'}, status=status.HTTP_403_FORBIDDEN)

        if not book.file:
            return Response({'detail': 'Book file is missing.'}, status=status.HTTP_404_NOT_FOUND)

        book.update_downloads()
        filename = book.file.name.rsplit('/', 1)[-1]
        response = FileResponse(book.file.open('rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class BookProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsReader]

    @extend_schema(
        summary='Update reading progress',
        description='Submit current page and update reading progress for the book.',
        tags=['Book Reading'],
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def post(self, request, slug):
        logger.info("POST /api/reading/books/%s/progress/ for user %s", slug, request.user.username)
        book = get_object_or_404(Book, slug=slug)

        if not can_user_read_book(request.user, book):
            return Response({'detail': 'You do not have access to read this book.'}, status=status.HTTP_403_FORBIDDEN)

        current_page = request.data.get('current_page')
        if current_page is None:
            return Response({'detail': 'current_page is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            current_page = int(current_page)
        except (TypeError, ValueError):
            return Response({'detail': 'current_page must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        if current_page < 0:
            return Response({'detail': 'current_page cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)

        if book.pages > 0 and current_page > book.pages:
            return Response(
                {'detail': f'current_page cannot exceed the total book pages ({book.pages}).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        history, _ = ReadingHistory.objects.get_or_create(
            reader=request.user.reader_profile,
            book=book,
        )
        history.update_progress(current_page, book.pages if book.pages > 0 else 1)
        sync_reader_books_read(history.reader)

        return Response(
            {
                'success': True,
                'history_id': str(history.pk),
                'last_page_read': history.last_page_read,
                'progress_percentage': history.progress_percentage,
                'is_completed': history.is_completed,
            }
        )


def can_user_read_book(user, book):
    if is_moderator_or_staff(user):
        return True

    if book.authors.filter(user=user).exists():
        return True

    return book.can_read(user)


def can_user_download_book(user, book):
    if is_moderator_or_staff(user):
        return True

    if book.authors.filter(user=user).exists():
        return True

    return book.can_download(user)


def sync_reader_books_read(reader_profile):
    completed_count = ReadingHistory.objects.filter(reader=reader_profile, is_completed=True).count()
    if reader_profile.books_read != completed_count:
        reader_profile.books_read = completed_count
        reader_profile.save(update_fields=['books_read'])
