"""API for reading and downloading books."""
import logging

from django.db import IntegrityError
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api_errors import error_response
from core.books.permissions import IsReader, is_moderator_or_staff
from core.books.reading_serializers import BookProgressResponseSerializer, BookReadResponseSerializer, ReadingHistorySerializer
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
        operation_id='reading_book_read',
        summary='Read book',
        description='Return book data for reading and create reading history if needed.',
        tags=['Book Reading'],
        responses={200: BookReadResponseSerializer, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        logger.info("GET /api/reading/books/%s/read/ for user %s", slug, request.user.username)

        book = self.get_object()
        if not can_user_read_book(request.user, book):
            return error_response(
                error_type='permission_denied',
                detail='You do not have access to read this book.',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        book.update_views()
        try:
            history, _ = ReadingHistory.objects.get_or_create(
                reader=request.user.reader_profile,
                book=book,
            )
        except IntegrityError:
            history = ReadingHistory.objects.get(reader=request.user.reader_profile, book=book)

        return Response(
            {
                'book': self.get_serializer(book, context={**self.get_serializer_context(), 'include_file_url': True}).data,
                'reading_history': ReadingHistorySerializer(history, context={'request': request}).data,
            }
        )


class BookDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsReader]

    @extend_schema(
        operation_id='reading_book_download',
        summary='Download book',
        description='Download the file of a book if downloading is allowed.',
        tags=['Book Reading'],
        responses={200: OpenApiTypes.BINARY, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, slug):
        logger.info("GET /api/reading/books/%s/download/ for user %s", slug, request.user.username)
        book = get_object_or_404(Book, slug=slug)

        if not can_user_download_book(request.user, book):
            return error_response(
                error_type='permission_denied',
                detail='You do not have access to download this book.',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        if not book.file:
            return error_response(
                error_type='not_found',
                detail='Book file is missing.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        book.update_downloads()
        filename = book.file.name.rsplit('/', 1)[-1]
        response = FileResponse(book.file.open('rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class BookProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsReader]

    @extend_schema(
        operation_id='reading_book_progress',
        summary='Update reading progress',
        description='Submit current page and update reading progress for the book.',
        tags=['Book Reading'],
        request=OpenApiTypes.OBJECT,
        responses={200: BookProgressResponseSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def post(self, request, slug):
        logger.info("POST /api/reading/books/%s/progress/ for user %s", slug, request.user.username)
        book = get_object_or_404(Book, slug=slug)

        if not can_user_read_book(request.user, book):
            return error_response(
                error_type='permission_denied',
                detail='You do not have access to read this book.',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        current_page = request.data.get('current_page')
        if current_page is None:
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'current_page': ['This field is required.']},
            )

        try:
            current_page = int(current_page)
        except (TypeError, ValueError):
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'current_page': ['current_page must be an integer.']},
            )

        if current_page < 0:
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'current_page': ['current_page cannot be negative.']},
            )

        if book.pages > 0 and current_page > book.pages:
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'current_page': [f'current_page cannot exceed the total book pages ({book.pages}).']},
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
