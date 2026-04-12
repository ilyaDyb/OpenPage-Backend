"""Views для книг и жанров."""
import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.response import Response

from core.books.models import Book, Genre
from core.books.serializers import (
    BookCreateUpdateSerializer,
    BookDetailSerializer,
    BookListSerializer,
    GenreSerializer,
)


logger = logging.getLogger(__name__)


class GenreListView(ListAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    @extend_schema(
        operation_id='books_genre_list',
        summary='Список жанров',
        description='Возвращает список всех жанров.',
        tags=['Genres'],
        responses={200: GenreSerializer},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/genres/")
        return super().get(request, *args, **kwargs)


class GenreDetailView(RetrieveAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id='books_genre_retrieve',
        summary='Детали жанра',
        description='Полная информация о жанре.',
        tags=['Genres'],
        responses={200: GenreSerializer, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/genres/%s/", kwargs.get('pk'))
        return super().get(request, *args, **kwargs)


class BookListView(ListAPIView):
    queryset = Book.objects.prefetch_related('authors', 'genres').filter(status='published', is_active=True)
    serializer_class = BookListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'description', 'authors__user__username']
    ordering_fields = ['title', 'created_at', 'updated_at', 'published_at', 'views_count', 'downloads_count', 'price']

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        genre_id = params.get('genres')
        if genre_id:
            queryset = queryset.filter(genres=genre_id)

        author_id = params.get('authors')
        if author_id:
            queryset = queryset.filter(authors=author_id)

        is_free = params.get('is_free')
        if is_free is not None:
            queryset = queryset.filter(is_free=is_free.lower() in {'1', 'true', 'yes'})

        status_value = params.get('status')
        if status_value:
            queryset = queryset.filter(status=status_value)

        price_lte = params.get('price__lte')
        if price_lte:
            queryset = queryset.filter(price__lte=price_lte)

        price_gte = params.get('price__gte')
        if price_gte:
            queryset = queryset.filter(price__gte=price_gte)

        pages_lte = params.get('pages__lte')
        if pages_lte:
            queryset = queryset.filter(pages__lte=pages_lte)

        pages_gte = params.get('pages__gte')
        if pages_gte:
            queryset = queryset.filter(pages__gte=pages_gte)

        return queryset.distinct()

    @extend_schema(
        operation_id='books_book_list',
        summary='Список книг',
        description='Возвращает список опубликованных книг с фильтрацией и поиском.',
        tags=['Books'],
        parameters=[
            OpenApiParameter(name='search', required=False, type=str, description='Поиск по названию и описанию'),
            OpenApiParameter(name='genres', required=False, type=str, description='ID жанров'),
            OpenApiParameter(name='is_free', required=False, type=bool, description='Только бесплатные'),
            OpenApiParameter(name='ordering', required=False, type=str, description='Сортировка'),
        ],
        responses={200: BookListSerializer},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/")
        return super().get(request, *args, **kwargs)


class BookDetailView(RetrieveAPIView):
    queryset = Book.objects.prefetch_related('authors', 'genres').all()
    serializer_class = BookDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    @extend_schema(
        operation_id='books_book_retrieve',
        summary='Детали книги',
        description='Полная информация о книге.',
        tags=['Books'],
        responses={200: BookDetailSerializer, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/%s/", kwargs.get('pk'))
        book = self.get_object()
        book.update_views()
        serializer = self.get_serializer(book)
        return Response(serializer.data)


class BookBySlugView(RetrieveAPIView):
    queryset = Book.objects.prefetch_related('authors', 'genres').all()
    serializer_class = BookDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'

    @extend_schema(
        operation_id='books_book_by_slug_retrieve',
        summary='Книга по slug',
        description='Получить книгу по slug.',
        tags=['Books'],
        responses={200: BookDetailSerializer, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/slug/%s/", kwargs.get('slug'))
        book = get_object_or_404(Book.objects.prefetch_related('authors', 'genres'), slug=kwargs['slug'])
        book.update_views()
        serializer = self.get_serializer(book)
        return Response(serializer.data)


class BookCreateView(CreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id='books_book_create',
        summary='Создать книгу',
        description='Создание новой книги для пользователя с профилем автора.',
        tags=['Books'],
        request=BookCreateUpdateSerializer,
        responses={201: BookDetailSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):
        logger.info("POST /api/books/create/ by user %s", request.user.username)
        if not hasattr(request.user, 'author_profile'):
            return Response(
                {'error': 'У вас нет профиля автора. Создайте профиль автора.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        author_profile = self.request.user.author_profile
        book = serializer.save()
        if not book.authors.filter(pk=author_profile.pk).exists():
            book.authors.add(author_profile)
        logger.info("Book '%s' created", book.title)


class BookUpdateView(UpdateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    @extend_schema(
        operation_id='books_book_update',
        summary='Обновить книгу',
        description='Обновление книги доступно только ее автору.',
        tags=['Books'],
        request=BookCreateUpdateSerializer,
        responses={
            200: BookDetailSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    )
    def put(self, request, *args, **kwargs):
        logger.info("PUT /api/books/%s/update/", kwargs.get('pk'))
        return super().put(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        logger.info("PATCH /api/books/%s/update/", kwargs.get('pk'))
        return super().patch(request, *args, **kwargs)

    def check_object_permissions(self, request, obj):
        if not obj.authors.filter(user=request.user).exists():
            self.permission_denied(request, message='Вы не являетесь автором этой книги')


class BookDeleteView(DestroyAPIView):
    queryset = Book.objects.all()
    serializer_class = BookDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    @extend_schema(
        operation_id='books_book_delete',
        summary='Удалить книгу',
        description='Удаление книги доступно только ее автору.',
        tags=['Books'],
        responses={204: None, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def delete(self, request, *args, **kwargs):
        logger.info("DELETE /api/books/%s/delete/", kwargs.get('pk'))
        return super().delete(request, *args, **kwargs)

    def check_object_permissions(self, request, obj):
        if not obj.authors.filter(user=request.user).exists():
            self.permission_denied(request, message='Вы не являетесь автором этой книги')


class MyBooksView(ListAPIView):
    serializer_class = BookListSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id='books_my_list',
        summary='Мои книги',
        description='Список всех книг текущего автора.',
        tags=['Books'],
        responses={200: BookListSerializer},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/my/")
        if not hasattr(request.user, 'author_profile'):
            return Response([], status=status.HTTP_200_OK)

        queryset = Book.objects.filter(authors=request.user.author_profile).prefetch_related('authors', 'genres')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
