# """
# Views для закладок, истории чтения и отзывов
# """
# import logging
# from rest_framework import status, permissions
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework.generics import (
#     ListAPIView, RetrieveAPIView, CreateAPIView,
#     UpdateAPIView, DestroyAPIView, get_object_or_404
# )
# from drf_spectacular.utils import extend_schema, OpenApiTypes
# from core.profiles.models import Bookmark, ReadingHistory, Review, ReaderProfile, AuthorProfile
# from core.books.reading_serializers import (
#     BookmarkSerializer,
#     ReadingHistorySerializer,
#     ReviewSerializer,
#     ReviewCreateSerializer
# )
# from core.books.permissions import IsOwner, IsReader, IsModerator

# logger = logging.getLogger(__name__)


# # ==================== Bookmark Views ====================

# class BookmarkListView(ListAPIView):
#     """Список закладок текущего читателя"""
#     serializer_class = BookmarkSerializer
#     permission_classes = [permissions.IsAuthenticated, IsReader]
    
#     @extend_schema(
#         summary="Мои закладки",
#         description="Список всех закладок текущего пользователя",
#         tags=['Reading Features'],
#         responses={200: BookmarkSerializer(many=True)}
#     )
#     def get(self, request, *args, **kwargs):
#         logger.info(f"📥 GET /api/bookmarks/ - Закладки пользователя: {request.user.username}")
        
#         reader_profile = request.user.reader_profile
#         queryset = Bookmark.objects.filter(reader=reader_profile).select_related('book')
        
#         serializer = self.get_serializer(queryset, many=True)
#         return Response(serializer.data)


# class BookmarkCreateView(CreateAPIView):
#     """Создание закладки"""
#     serializer_class = BookmarkSerializer
#     permission_classes = [permissions.IsAuthenticated, IsReader]
    
#     @extend_schema(
#         summary="Добавить закладку",
#         description="Создать новую закладку для книги",
#         tags=['Reading Features'],
#         request=BookmarkSerializer,
#         responses={
#             201: BookmarkSerializer,
#             400: OpenApiTypes.OBJECT
#         }
#     )
#     def post(self, request, *args, **kwargs):
#         logger.info(f"📝 POST /api/bookmarks/ - Создание закладки: {request.user.username}")
#         return super().post(request, *args, **kwargs)
    
#     def perform_create(self, serializer):
#         """Сохраняем закладку с текущим читателем"""
#         reader_profile = self.request.user.reader_profile
        
#         # Проверяем, существует ли уже такая закладка
#         book = serializer.validated_data.get('book')
#         page_number = serializer.validated_data.get('page_number')
        
#         existing = Bookmark.objects.filter(
#             reader=reader_profile,
#             book=book,
#             page_number=page_number
#         ).first()
        
#         if existing:
#             raise Exception("Такая закладка уже существует")
        
#         serializer.save(reader=reader_profile)
#         logger.info(f"✅ Закладка создана: книга {book.title}, стр. {page_number}")


# class BookmarkDeleteView(DestroyAPIView):
#     """Удаление закладки"""
#     serializer_class = BookmarkSerializer
#     permission_classes = [permissions.IsAuthenticated, IsOwner]
#     queryset = Bookmark.objects.all()
#     lookup_field = 'pk'
    
#     @extend_schema(
#         summary="Удалить закладку",
#         description="Удалить закладку по ID",
#         tags=['Reading Features'],
#         responses={204: None, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
#     )
#     def delete(self, request, *args, **kwargs):
#         pk = kwargs.get('pk')
#         logger.info(f"🗑️ DELETE /api/bookmarks/{pk}/ - Удаление закладки")
#         return super().delete(request, *args, **kwargs)


# # ==================== Reading History Views ====================

# class ReadingHistoryListView(ListAPIView):
#     """Список истории чтения текущего читателя"""
#     serializer_class = ReadingHistorySerializer
#     permission_classes = [permissions.IsAuthenticated, IsReader]
    
#     @extend_schema(
#         summary="История чтения",
#         description="Список всех книг в истории чтения с прогрессом",
#         tags=['Reading Features'],
#         responses={200: ReadingHistorySerializer(many=True)}
#     )
#     def get(self, request, *args, **kwargs):
#         logger.info(f"📥 GET /api/reading-history/ - История чтения: {request.user.username}")
        
#         reader_profile = request.user.reader_profile
#         queryset = ReadingHistory.objects.filter(
#             reader=reader_profile
#         ).select_related('book').order_by('-started_at')
        
#         serializer = self.get_serializer(queryset, many=True)
#         return Response(serializer.data)


# class ReadingHistoryCreateView(CreateAPIView):
#     """Начать чтение книги (создать запись в истории)"""
#     serializer_class = ReadingHistorySerializer
#     permission_classes = [permissions.IsAuthenticated, IsReader]
    
#     @extend_schema(
#         summary="Начать чтение",
#         description="Создать запись в истории чтения для новой книги",
#         tags=['Reading Features'],
#         request=ReadingHistorySerializer,
#         responses={
#             201: ReadingHistorySerializer,
#             400: OpenApiTypes.OBJECT
#         }
#     )
#     def post(self, request, *args, **kwargs):
#         logger.info(f"📝 POST /api/reading-history/ - Начало чтения: {request.user.username}")
#         return super().post(request, *args, **kwargs)
    
#     def perform_create(self, serializer):
#         """Сохраняем историю с текущим читателем"""
#         reader_profile = self.request.user.reader_profile
#         serializer.save(reader=reader_profile)


# class ReadingHistoryUpdateView(UpdateAPIView):
#     """Обновление прогресса чтения"""
#     serializer_class = ReadingHistorySerializer
#     permission_classes = [permissions.IsAuthenticated, IsOwner]
#     queryset = ReadingHistory.objects.all()
#     lookup_field = 'pk'
    
#     @extend_schema(
#         summary="Обновить прогресс",
#         description="Обновить прогресс чтения книги (номер страницы)",
#         tags=['Reading Features'],
#         request=ReadingHistorySerializer,
#         responses={
#             200: ReadingHistorySerializer,
#             400: OpenApiTypes.OBJECT,
#             403: OpenApiTypes.OBJECT
#         }
#     )
#     def patch(self, request, *args, **kwargs):
#         pk = kwargs.get('pk')
#         logger.info(f"🔧 PATCH /api/reading-history/{pk}/ - Обновление прогресса")
#         return super().patch(request, *args, **kwargs)
    
#     def partial_update(self, request, *args, **kwargs):
#         """Частичное обновление"""
#         instance = self.get_object()
#         last_page_read = request.data.get('last_page_read')
        
#         if last_page_read is not None:
#             total_pages = instance.book.pages if instance.book.pages > 0 else 1
#             instance.update_progress(int(last_page_read), total_pages)
#             logger.info(f"✅ Прогресс обновлен: {instance.progress_percentage}%")
        
#         serializer = self.get_serializer(instance)
#         return Response(serializer.data)


# # ==================== Review Views ====================

# class ReviewListView(ListAPIView):
#     """Список отзывов с фильтрацией"""
#     serializer_class = ReviewSerializer
#     permission_classes = [permissions.IsAuthenticated]
    
#     @extend_schema(
#         summary="Список отзывов",
#         description="Список всех отзывов или отзывов для конкретной книги",
#         tags=['Reading Features'],
#         parameters=[],
#         responses={200: ReviewSerializer(many=True)}
#     )
#     def get(self, request, *args, **kwargs):
#         logger.info(f"📥 GET /api/reviews/ - Список отзывов")
        
#         book_id = request.query_params.get('book')
        
#         if book_id:
#             queryset = Review.objects.filter(book_id=book_id).select_related('reader__user', 'book')
#         else:
#             queryset = Review.objects.all().select_related('reader__user', 'book').order_by('-created_at')
        
#         serializer = self.get_serializer(queryset, many=True)
#         return Response(serializer.data)


# class ReviewCreateView(CreateAPIView):
#     """Создание отзыва"""
#     serializer_class = ReviewCreateSerializer
#     permission_classes = [permissions.IsAuthenticated, IsReader]
    
#     @extend_schema(
#         summary="Оставить отзыв",
#         description="Создать новый отзыв на книгу (один отзыв на книгу)",
#         tags=['Reading Features'],
#         request=ReviewCreateSerializer,
#         responses={
#             201: ReviewSerializer,
#             400: OpenApiTypes.OBJECT
#         }
#     )
#     def post(self, request, *args, **kwargs):
#         logger.info(f"📝 POST /api/reviews/ - Создание отзыва: {request.user.username}")
#         return super().post(request, *args, **kwargs)
    
#     def perform_create(self, serializer):
#         """Сохраняем отзыв с текущим читателем"""
#         reader_profile = self.request.user.reader_profile
#         serializer.save(reader=reader_profile)
#         logger.info(f"✅ Отзыв создан на книгу: {serializer.validated_data['book'].title}")


# class ReviewDetailView(RetrieveAPIView):
#     """Детальный просмотр отзыва"""
#     queryset = Review.objects.all()
#     serializer_class = ReviewSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     lookup_field = 'pk'
    
#     @extend_schema(
#         summary="Детали отзыва",
#         description="Полная информация об отзыве",
#         tags=['Reading Features'],
#         responses={200: ReviewSerializer, 404: OpenApiTypes.OBJECT}
#     )
#     def get(self, request, *args, **kwargs):
#         pk = kwargs.get('pk')
#         logger.info(f"📥 GET /api/reviews/{pk}/ - Детали отзыва")
#         return super().get(request, *args, **kwargs)


# class ReviewHelpfulView(APIView):
#     """Голосование за полезность отзыва"""
#     permission_classes = [permissions.IsAuthenticated]
    
#     @extend_schema(
#         summary="Отметить как полезный",
#         description="Увеличить счетчик полезных голосов отзыва",
#         tags=['Reading Features'],
#         responses={
#             200: OpenApiTypes.OBJECT,
#             404: OpenApiTypes.OBJECT
#         }
#     )
#     def post(self, request, pk):
#         logger.info(f"👍 POST /api/reviews/{pk}/helpful/ - Голос за полезность")
        
#         review = get_object_or_404(Review, pk=pk)
#         review.mark_as_helpful()
        
#         return Response({
#             'success': True,
#             'helpful_count': review.helpful_count
#         })


# class ReviewDeleteView(DestroyAPIView):
#     """Удаление отзыва"""
#     queryset = Review.objects.all()
#     serializer_class = ReviewSerializer
#     permission_classes = [permissions.IsAuthenticated, IsOwner]
#     lookup_field = 'pk'
    
#     @extend_schema(
#         summary="Удалить отзыв",
#         description="Удалить свой отзыв",
#         tags=['Reading Features'],
#         responses={204: None, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
#     )
#     def delete(self, request, *args, **kwargs):
#         pk = kwargs.get('pk')
#         logger.info(f"🗑️ DELETE /api/reviews/{pk}/ - Удаление отзыва")
#         return super().delete(request, *args, **kwargs)


# # ==================== Author Request Views ====================

# class AuthorRequestView(APIView):
#     """Запрос на получение статуса автора"""
#     permission_classes = [permissions.IsAuthenticated]
    
#     @extend_schema(
#         summary="Запросить статус автора",
#         description="Создать профиль автора с запросом на модерацию",
#         tags=['Author Management'],
#         responses={
#             201: OpenApiTypes.OBJECT,
#             400: OpenApiTypes.OBJECT
#         }
#     )
#     def post(self, request):
#         logger.info(f"📝 POST /api/author/request/ - Запрос статуса автора: {request.user.username}")
        
#         # Проверяем, есть ли уже профиль автора
#         if hasattr(request.user, 'author_profile'):
#             author_profile = request.user.author_profile
            
#             if author_profile.is_approved:
#                 return Response(
#                     {'error': 'У вас уже есть подтвержденный профиль автора'},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
            
#             return Response(
#                 {
#                     'message': 'Ваш запрос уже отправлен и ожидает модерации',
#                     'requested_at': author_profile.requested_at
#                 },
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Создаем профиль автора
#         bio = request.data.get('bio', '')
#         website = request.data.get('website', '')
#         telegram = request.data.get('telegram', '')
#         vkontakte = request.data.get('vkontakte', '')
        
#         author_profile = AuthorProfile.objects.create(
#             user=request.user,
#             bio=bio,
#             website=website,
#             telegram=telegram,
#             vkontakte=vkontakte,
#             is_approved=False,
#             requested_at=timezone.now()
#         )
        
#         logger.info(f"✅ Создан запрос на статус автора: {request.user.username}")
        
#         return Response({
#             'message': 'Запрос отправлен на модерацию',
#             'author_profile': {
#                 'id': author_profile.id,
#                 'is_approved': author_profile.is_approved,
#                 'requested_at': author_profile.requested_at
#             }
#         }, status=status.HTTP_201_CREATED)


# class AuthorRequestsListView(ListAPIView):
#     """Список запросов на статус автора (для модераторов)"""
#     serializer_class = None  # Будет переопределено
#     permission_classes = [permissions.IsAuthenticated, IsModerator]
    
#     @extend_schema(
#         summary="Все запросы авторов",
#         description="Список всех неподтвержденных запросов на статус автора",
#         tags=['Author Management'],
#         responses={200: OpenApiTypes.OBJECT}
#     )
#     def get(self, request, *args, **kwargs):
#         logger.info(f"📥 GET /api/author/requests/ - Запросы авторов (модератор)")
        
#         requests = AuthorProfile.objects.filter(
#             is_approved=False
#         ).select_related('user').order_by('requested_at')
        
#         data = []
#         for author in requests:
#             data.append({
#                 'id': author.id,
#                 'username': author.user.username,
#                 'email': author.user.email,
#                 'full_name': author.full_name,
#                 'bio': author.bio,
#                 'website': author.website,
#                 'telegram': author.telegram,
#                 'requested_at': author.requested_at
#             })
        
#         return Response(data)


# class AuthorRequestModerateView(APIView):
#     """Модерация запроса на статус автора"""
#     permission_classes = [permissions.IsAuthenticated, IsModerator]
    
#     @extend_schema(
#         summary="Модерировать запрос",
#         description="Подтвердить или отклонить запрос на статус автора",
#         tags=['Author Management'],
#         request=OpenApiTypes.OBJECT,
#         responses={
#             200: OpenApiTypes.OBJECT,
#             400: OpenApiTypes.OBJECT,
#             404: OpenApiTypes.OBJECT
#         }
#     )
#     def patch(self, request, pk):
#         logger.info(f"🔧 PATCH /api/author/requests/{pk}/moderate/ - Модерация запроса")
        
#         author_profile = get_object_or_404(AuthorProfile, pk=pk)
        
#         approve = request.data.get('approve')
#         rejection_reason = request.data.get('rejection_reason', '')
        
#         if approve:
#             author_profile.is_approved = True
#             author_profile.approved_at = timezone.now()
#             author_profile.save(update_fields=['is_approved', 'approved_at'])
            
#             logger.info(f"✅ Запрос одобрен: {author_profile.user.username}")
            
#             return Response({
#                 'message': 'Автор подтвержден',
#                 'approved_at': author_profile.approved_at
#             })
#         else:
#             # Отклоняем запрос
#             if rejection_reason:
#                 logger.info(f"❌ Запрос отклонен: {rejection_reason}")
            
#             # Удаляем профиль автора (или можно просто установить флаг)
#             author_profile.delete()
            
#             return Response({
#                 'message': 'Запрос отклонен',
#                 'reason': rejection_reason
#             })


# # Импорты
# from django.utils import timezone
