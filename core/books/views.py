"""Views for books and genres."""
import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
    UpdateAPIView,
    get_object_or_404,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from core.books.models import Book, BookComment, BookLike, Genre
from core.books.permissions import (
    CanViewBook,
    HasAuthorProfile,
    IsApprovedAuthor,
    IsBookAuthorOrStaff,
    IsModeratorOrStaff,
    IsOwner,
    IsReader,
)
from core.books.reading_serializers import ensure_reader_book_access
from core.books.serializers import (
    BookCommentCreateSerializer,
    BookCommentSerializer,
    BookCreateUpdateSerializer,
    BookDetailSerializer,
    BookLikeResponseSerializer,
    BookListSerializer,
    GenreSerializer,
)


logger = logging.getLogger(__name__)


class GenreListCreateView(ListCreateAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description', 'slug']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsModeratorOrStaff()]
        return [permissions.IsAuthenticated()]

    @extend_schema(
        operation_id='books_genre_list',
        summary='List genres',
        description='Returns all genres.',
        tags=['Genres'],
        responses={200: GenreSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/genres/")
        return super().get(request, *args, **kwargs)

    @extend_schema(
        operation_id='books_genre_create',
        summary='Create genre',
        description='Create a new genre. Available to moderators and staff.',
        tags=['Genres'],
        request=GenreSerializer,
        responses={201: GenreSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):
        logger.info("POST /api/books/genres/")
        return super().post(request, *args, **kwargs)


class GenreDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsModeratorOrStaff()]

    @extend_schema(
        operation_id='books_genre_retrieve',
        summary='Genre details',
        description='Get full genre details.',
        tags=['Genres'],
        responses={200: GenreSerializer, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/genres/%s/", kwargs.get('pk'))
        return super().get(request, *args, **kwargs)

    @extend_schema(
        operation_id='books_genre_update',
        summary='Update genre',
        description='Update a genre. Available to moderators and staff.',
        tags=['Genres'],
        request=GenreSerializer,
        responses={200: GenreSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def patch(self, request, *args, **kwargs):
        logger.info("PATCH /api/books/genres/%s/", kwargs.get('pk'))
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        operation_id='books_genre_replace',
        summary='Replace genre',
        description='Replace a genre. Available to moderators and staff.',
        tags=['Genres'],
        request=GenreSerializer,
        responses={200: GenreSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def put(self, request, *args, **kwargs):
        logger.info("PUT /api/books/genres/%s/", kwargs.get('pk'))
        return super().put(request, *args, **kwargs)

    @extend_schema(
        operation_id='books_genre_delete',
        summary='Delete genre',
        description='Delete a genre. Available to moderators and staff.',
        tags=['Genres'],
        responses={204: None, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def delete(self, request, *args, **kwargs):
        logger.info("DELETE /api/books/genres/%s/", kwargs.get('pk'))
        return super().delete(request, *args, **kwargs)


class BookListView(ListAPIView):
    serializer_class = BookListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'description', 'authors__user__username', 'slug']
    ordering_fields = ['title', 'created_at', 'updated_at', 'published_at', 'views_count', 'downloads_count', 'price']

    def get_queryset(self):
        queryset = Book.objects.prefetch_related('authors', 'genres', 'likes').filter(status='published', is_active=True)
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
        summary='List books',
        description='Returns published books with filtering and search.',
        tags=['Books'],
        parameters=[
            OpenApiParameter(name='search', required=False, type=str),
            OpenApiParameter(name='genres', required=False, type=str),
            OpenApiParameter(name='authors', required=False, type=str),
            OpenApiParameter(name='is_free', required=False, type=bool),
            OpenApiParameter(name='price__lte', required=False, type=str),
            OpenApiParameter(name='price__gte', required=False, type=str),
            OpenApiParameter(name='pages__lte', required=False, type=str),
            OpenApiParameter(name='pages__gte', required=False, type=str),
            OpenApiParameter(name='ordering', required=False, type=str),
        ],
        responses={200: BookListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/")
        return super().get(request, *args, **kwargs)


class BookDetailView(RetrieveAPIView):
    queryset = Book.objects.prefetch_related('authors', 'genres', 'likes', 'comments').all()
    serializer_class = BookDetailSerializer
    permission_classes = [permissions.IsAuthenticated, CanViewBook]
    lookup_field = 'pk'

    @extend_schema(
        operation_id='books_book_retrieve',
        summary='Book details',
        description='Returns full book details.',
        tags=['Books'],
        responses={200: BookDetailSerializer, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/%s/", kwargs.get('pk'))
        book = self.get_object()
        book.update_views()
        serializer = self.get_serializer(book)
        return Response(serializer.data)


class BookBySlugView(RetrieveAPIView):
    queryset = Book.objects.prefetch_related('authors', 'genres', 'likes', 'comments').all()
    serializer_class = BookDetailSerializer
    permission_classes = [permissions.IsAuthenticated, CanViewBook]
    lookup_field = 'slug'

    @extend_schema(
        operation_id='books_book_by_slug_retrieve',
        summary='Book by slug',
        description='Get a book by slug.',
        tags=['Books'],
        responses={200: BookDetailSerializer, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/slug/%s/", kwargs.get('slug'))
        book = self.get_object()
        book.update_views()
        serializer = self.get_serializer(book)
        return Response(serializer.data)


class BookCreateView(CreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsApprovedAuthor]

    @extend_schema(
        operation_id='books_book_create',
        summary='Create book',
        description='Create a new book. Only approved authors can create books.',
        tags=['Books'],
        request=BookCreateUpdateSerializer,
        responses={201: BookDetailSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):
        logger.info("POST /api/books/create/ by user %s", request.user.username)
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        book = serializer.instance
        output = BookDetailSerializer(book, context=self.get_serializer_context())
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=201, headers=headers)

    def perform_create(self, serializer):
        author_profile = self.request.user.author_profile
        book = serializer.save()
        if not book.authors.filter(pk=author_profile.pk).exists():
            book.authors.add(author_profile)
        logger.info("Book '%s' created", book.title)


class BookUpdateView(UpdateAPIView):
    queryset = Book.objects.prefetch_related('authors', 'genres').all()
    serializer_class = BookCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsBookAuthorOrStaff]
    lookup_field = 'pk'

    @extend_schema(
        operation_id='books_book_update',
        summary='Update book',
        description='Only the book author, moderator, or staff can update the book.',
        tags=['Books'],
        request=BookCreateUpdateSerializer,
        responses={200: BookDetailSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def put(self, request, *args, **kwargs):
        logger.info("PUT /api/books/%s/update/", kwargs.get('pk'))
        return super().put(request, *args, **kwargs)

    @extend_schema(
        operation_id='books_book_partial_update',
        summary='Partially update book',
        description='Partially update a book. Only the book author, moderator, or staff can update the book.',
        tags=['Books'],
        request=BookCreateUpdateSerializer,
        responses={200: BookDetailSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def patch(self, request, *args, **kwargs):
        logger.info("PATCH /api/books/%s/update/", kwargs.get('pk'))
        return super().patch(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        output = BookDetailSerializer(serializer.instance, context=self.get_serializer_context())
        return Response(output.data)


class BookDeleteView(DestroyAPIView):
    queryset = Book.objects.prefetch_related('authors', 'genres').all()
    serializer_class = BookDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsBookAuthorOrStaff]
    lookup_field = 'pk'

    @extend_schema(
        operation_id='books_book_delete',
        summary='Delete book',
        description='Only the book author, moderator, or staff can delete the book.',
        tags=['Books'],
        responses={204: None, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def delete(self, request, *args, **kwargs):
        logger.info("DELETE /api/books/%s/delete/", kwargs.get('pk'))
        return super().delete(request, *args, **kwargs)


class MyBooksView(ListAPIView):
    serializer_class = BookListSerializer
    permission_classes = [permissions.IsAuthenticated, HasAuthorProfile]

    def get_queryset(self):
        try:
            author_profile = self.request.user.author_profile
        except Exception:
            author_profile = None
        if not author_profile:
            return Book.objects.none()

        return Book.objects.filter(authors=author_profile).prefetch_related('authors', 'genres', 'likes')

    @extend_schema(
        operation_id='books_my_list',
        summary='My books',
        description='List all books created by the current author.',
        tags=['Books'],
        responses={200: BookListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/my/")
        return super().get(request, *args, **kwargs)


class BookLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsReader]

    @extend_schema(
        operation_id='books_book_like',
        summary='Like book',
        description='Create a like for a book or return the current liked state.',
        tags=['Books'],
        request=None,
        responses={200: BookLikeResponseSerializer, 201: BookLikeResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def post(self, request, pk):
        logger.info("POST /api/books/%s/like/ by user %s", pk, request.user.username)
        book = get_book_for_interaction(request, pk)
        _, created = BookLike.objects.get_or_create(reader=request.user.reader_profile, book=book)
        return Response(
            {
                'success': True,
                'liked': True,
                'likes_count': get_book_likes_count(book),
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id='books_book_unlike',
        summary='Unlike book',
        description='Delete the current reader like from a book.',
        tags=['Books'],
        request=None,
        responses={200: BookLikeResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def delete(self, request, pk):
        logger.info("DELETE /api/books/%s/like/ by user %s", pk, request.user.username)
        book = get_book_for_interaction(request, pk)
        BookLike.objects.filter(reader=request.user.reader_profile, book=book).delete()
        return Response(
            {
                'success': True,
                'liked': False,
                'likes_count': get_book_likes_count(book),
            }
        )


class BookCommentListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsReader()]
        return [permissions.IsAuthenticated()]

    def get_book(self):
        if not hasattr(self, '_book'):
            self._book = get_book_for_interaction(self.request, self.kwargs['pk'])
        return self._book

    def get_queryset(self):
        return (
            BookComment.objects
            .filter(book=self.get_book(), parent__isnull=True)
            .select_related('reader__user', 'book')
            .prefetch_related('replies__reader__user')
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BookCommentCreateSerializer
        return BookCommentSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['book'] = self.get_book()
        return context

    @extend_schema(
        operation_id='books_book_comment_list',
        summary='List book comments',
        description='List top-level comments for a book with nested replies.',
        tags=['Books'],
        responses={200: BookCommentSerializer(many=True), 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/%s/comments/", kwargs.get('pk'))
        return super().get(request, *args, **kwargs)

    @extend_schema(
        operation_id='books_book_comment_create',
        summary='Create book comment',
        description='Create a top-level comment or a reply for a book.',
        tags=['Books'],
        request=BookCommentCreateSerializer,
        responses={201: BookCommentSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):
        logger.info("POST /api/books/%s/comments/ by user %s", kwargs.get('pk'), request.user.username)
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()
        output = BookCommentSerializer(comment, context=self.get_serializer_context())
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)


class BookCommentDetailView(RetrieveAPIView):
    queryset = BookComment.objects.select_related('reader__user', 'book', 'parent').prefetch_related('replies__reader__user')
    serializer_class = BookCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    @extend_schema(
        operation_id='books_book_comment_retrieve',
        summary='Book comment details',
        description='Get a comment with its direct replies.',
        tags=['Books'],
        responses={200: BookCommentSerializer, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        logger.info("GET /api/books/comments/%s/", kwargs.get('pk'))
        return super().get(request, *args, **kwargs)


class BookCommentDeleteView(DestroyAPIView):
    queryset = BookComment.objects.select_related('reader__user', 'book', 'parent')
    serializer_class = BookCommentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    lookup_field = 'pk'

    @extend_schema(
        operation_id='books_book_comment_delete',
        summary='Delete book comment',
        description='Delete your own book comment or reply.',
        tags=['Books'],
        responses={204: None, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def delete(self, request, *args, **kwargs):
        logger.info("DELETE /api/books/comments/%s/delete/", kwargs.get('pk'))
        return super().delete(request, *args, **kwargs)


def get_book_for_interaction(request, pk):
    book = get_object_or_404(
        Book.objects.prefetch_related('authors', 'genres', 'likes', 'comments'),
        pk=pk,
    )
    ensure_reader_book_access(request.user, book, require_read_access=False)
    return book


def get_book_likes_count(book):
    return BookLike.objects.filter(book=book).count()
