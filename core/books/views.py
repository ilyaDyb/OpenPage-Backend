# """
# Views для книг и жанров
# """
# import logging
# from rest_framework import status, permissions
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework.generics import (
#     ListAPIView, RetrieveAPIView, CreateAPIView,
#     UpdateAPIView, DestroyAPIView, get_object_or_404
# )
# from rest_framework.filters import SearchFilter, OrderingFilter
# from django_filters.rest_framework import DjangoFilterBackend
# from drf_spectacular.utils import extend_schema, OpenApiTypes, OpenApiParameter
# from core.books.models import Genre, Book
# from core.books.serializers import (
#     GenreSerializer,
#     BookListSerializer,
#     BookDetailSerializer,
#     BookCreateUpdateSerializer
# )
# from core.profiles.models import AuthorProfile

# logger = logging.getLogger(__name__)


# # ==================== Genre Views ====================

# class GenreListView(ListAPIView):
#     """Список всех жанров"""
#     queryset = Genre.objects.all()
#     serializer_class = GenreSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [SearchFilter, OrderingFilter]
#     search_fields = ['name', 'description']
#     ordering_fields = ['name', 'created_at', 'books_count']
    
#     @extend_schema(
#         summary="Список жанров",
#         description="Возвращает список всех жанров с количеством книг",
#         tags=['Genres'],
#         responses={200: GenreSerializer}
#     )
#     def get(self, request, *args, **kwargs):
#         logger.info(f"📥 GET /api/books/genres/ - Список жанров")
#         return super().get(request, *args, **kwargs)


# class GenreDetailView(RetrieveAPIView):
#     """Детальный просмотр жанра"""
#     queryset = Genre.objects.all()
#     serializer_class = GenreSerializer
#     permission_classes = [permissions.IsAuthenticated]
    
#     @extend_schema(
#         summary="Детали жанра",
#         description="Полная информация о жанре",
#         tags=['Genres'],
#         responses={200: GenreSerializer, 404: OpenApiTypes.OBJECT}
#     )
#     def get(self, request, *args, **kwargs):
#         pk = kwargs.get('pk')
#         logger.info(f"📥 GET /api/books/genres/{pk}/ - Детали жанра")
#         return super().get(request, *args, **kwargs)


# # ==================== Book Views ====================

# class BookListView(ListAPIView):
#     """Список всех книг с фильтрацией"""
#     queryset = Book.objects.select_related().prefetch_related('authors', 'genres').filter(
#         status='published',
#         is_active=True
#     )
#     serializer_class = BookListSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
#     filterset_fields = {
#         'genres': ['exact', 'in'],
#         'authors': ['exact'],
#         'is_free': ['exact'],
#         'status': ['exact'],
#         'price': ['lte', 'gte'],
#         'pages': ['lte', 'gte'],
#     }
#     search_fields = ['title', 'description', 'authors__user__username']
#     ordering_fields = [
#         'title', 'created_at', 'updated_at', 'published_at',
#         'views_count', 'downloads_count', 'price'
#     ]
    
#     @extend_schema(
#         summary="Список книг",
#         description="Возвращает список опубликованных книг с фильтрацией и поиском",
#         tags=['Books'],
#         parameters=[
#             OpenApiParameter(name='search', description='Поиск по названию и описанию', required=False, type=str),
#             OpenApiParameter(name='genres', description='ID жанров (через запятую)', required=False, type=str),
#             OpenApiParameter(name='is_free', description='Только бесплатные', required=False, type=bool),
#             OpenApiParameter(name='ordering', description='Сортировка (например: -created_at)', required=False, type=str),
#         ],
#         responses={200: BookListSerializer}
#     )
#     def get(self, request, *args, **kwargs):
#         logger.info(f"📥 GET /api/books/ - Список книг")
#         return super().get(request, *args, **kwargs)


# class BookDetailView(RetrieveAPIView):
#     """Детальный просмотр книги"""
#     queryset = Book.objects.select_related().prefetch_related('authors', 'genres').all()
#     serializer_class = BookDetailSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     lookup_field = 'pk'
    
#     @extend_schema(
#         summary="Детали книги",
#         description="Полная информация о книге включая авторов и жанры",
#         tags=['Books'],
#         responses={200: BookDetailSerializer, 404: OpenApiTypes.OBJECT}
#     )
#     def get(self, request, *args, **kwargs):
#         pk = kwargs.get('pk')
#         logger.info(f"📥 GET /api/books/{pk}/ - Детали книги")
        
#         # Увеличиваем счетчик просмотров
#         book = self.get_object()
#         book.update_views()
        
#         return super().get(request, *args, **kwargs)


# class BookBySlugView(RetrieveAPIView):
#     """Просмотр книги по slug"""
#     queryset = Book.objects.select_related().prefetch_related('authors', 'genres').all()
#     serializer_class = BookDetailSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     lookup_field = 'slug'
    
#     @extend_schema(
#         summary="Книга по slug",
#         description="Получить книгу по уникальному slug",
#         tags=['Books'],
#         responses={200: BookDetailSerializer, 404: OpenApiTypes.OBJECT}
#     )
#     def get(self, request, *args, **kwargs):
#         slug = kwargs.get('slug')
#         logger.info(f"📥 GET /api/books/slug/{slug}/ - Книга по slug")
        
#         book = get_object_or_404(Book, slug=slug)
#         book.update_views()
        
#         serializer = self.get_serializer(book)
#         return Response(serializer.data)


# class BookCreateView(CreateAPIView):
#     """Создание книги (только для авторов)"""
#     queryset = Book.objects.all()
#     serializer_class = BookCreateUpdateSerializer
#     permission_classes = [permissions.IsAuthenticated]
    
#     @extend_schema(
#         summary="Создать книгу",
#         description="Создание новой книги (доступно только пользователям с профилем автора)",
#         tags=['Books'],
#         request=BookCreateUpdateSerializer,
#         responses={
#             201: BookDetailSerializer,
#             400: OpenApiTypes.OBJECT,
#             403: OpenApiTypes.OBJECT
#         }
#     )
#     def post(self, request, *args, **kwargs):
#         logger.info(f"📝 POST /api/books/create/ - Создание книги пользователем: {request.user.username}")
        
#         # Проверяем, есть ли у пользователя профиль автора
#         if not hasattr(request.user, 'author_profile'):
#             return Response(
#                 {'error': 'У вас нет профиля автора. Создайте профиль автора.'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         return super().post(request, *args, **kwargs)
    
#     def perform_create(self, serializer):
#         """Сохраняем книгу и добавляем текущего автора"""
#         author_profile = self.request.user.author_profile
#         book = serializer.save()
#         book.authors.add(author_profile)
#         logger.info(f"✅ Книга '{book.title}' успешно создана")


# class BookUpdateView(UpdateAPIView):
#     """Обновление книги (только для авторов)"""
#     queryset = Book.objects.all()
#     serializer_class = BookCreateUpdateSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     lookup_field = 'pk'
    
#     @extend_schema(
#         summary="Обновить книгу",
#         description="Обновление книги (доступно только авторам этой книги)",
#         tags=['Books'],
#         request=BookCreateUpdateSerializer,
#         responses={
#             200: BookDetailSerializer,
#             400: OpenApiTypes.OBJECT,
#             403: OpenApiTypes.OBJECT,
#             404: OpenApiTypes.OBJECT
#         }
#     )
#     def put(self, request, *args, **kwargs):
#         pk = kwargs.get('pk')
#         logger.info(f"📝 PUT /api/books/{pk}/update/ - Обновление книги")
#         return super().put(request, *args, **kwargs)
    
#     def patch(self, request, *args, **kwargs):
#         pk = kwargs.get('pk')
#         logger.info(f"🔧 PATCH /api/books/{pk}/update/ - Частичное обновление книги")
#         return super().patch(request, *args, **kwargs)
    
#     def check_object_permissions(self, request, obj):
#         """Проверяем, что пользователь является автором книги"""
#         if not obj.authors.filter(user=request.user).exists():
#             self.permission_denied(
#                 request,
#                 message='Вы не являетесь автором этой книги'
#             )


# class BookDeleteView(DestroyAPIView):
#     """Удаление книги (только для авторов)"""
#     queryset = Book.objects.all()
#     serializer_class = BookDetailSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     lookup_field = 'pk'
    
#     @extend_schema(
#         summary="Удалить книгу",
#         description="Удаление книги (доступно только авторам этой книги)",
#         tags=['Books'],
#         responses={
#             204: None,
#             403: OpenApiTypes.OBJECT,
#             404: OpenApiTypes.OBJECT
#         }
#     )
#     def delete(self, request, *args, **kwargs):
#         pk = kwargs.get('pk')
#         logger.info(f"🗑️ DELETE /api/books/{pk}/delete/ - Удаление книги")
#         return super().delete(request, *args, **kwargs)
    
#     def check_object_permissions(self, request, obj):
#         """Проверяем, что пользователь является автором книги"""
#         if not obj.authors.filter(user=request.user).exists():
#             self.permission_denied(
#                 request,
#                 message='Вы не являетесь автором этой книги'
#             )


# class MyBooksView(ListAPIView):
#     """Список книг текущего пользователя"""
#     serializer_class = BookListSerializer
#     permission_classes = [permissions.IsAuthenticated]
    
#     @extend_schema(
#         summary="Мои книги",
#         description="Список всех книг текущего пользователя",
#         tags=['Books'],
#         responses={200: BookListSerializer}
#     )
#     def get(self, request, *args, **kwargs):
#         logger.info(f"📥 GET /api/books/my/ - Мои книги")
        
#         # Проверяем, есть ли профиль автора
#         if not hasattr(request.user, 'author_profile'):
#             return Response([], status=status.HTTP_200_OK)
        
#         author_profile = request.user.author_profile
#         queryset = Book.objects.filter(
#             authors=author_profile
#         ).select_related().prefetch_related('authors', 'genres')
        
#         serializer = self.get_serializer(queryset, many=True)
#         return Response(serializer.data)
