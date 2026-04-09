# """
# API для чтения и скачивания книг
# """
# import logging
# from rest_framework import status, permissions
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework.generics import RetrieveAPIView, get_object_or_404
# from drf_spectacular.utils import extend_schema, OpenApiTypes
# from django.http import FileResponse
# from django.conf import settings
# from core.books.models import Book
# from core.books.serializers import BookDetailSerializer
# from core.books.reading_serializers import ReadingHistorySerializer
# from core.books.permissions import IsReader

# logger = logging.getLogger(__name__)


# class BookReadView(RetrieveAPIView):
#     """
#     Эндпоинт для чтения книги
#     Возвращает информацию о книге и содержимое для чтения
#     """
#     queryset = Book.objects.select_related().prefetch_related('authors', 'genres').all()
#     serializer_class = BookDetailSerializer
#     permission_classes = [permissions.IsAuthenticated, IsReader]
#     lookup_field = 'slug'
    
#     @extend_schema(
#         summary="Читать книгу",
#         description="Получить данные книги для чтения (только если is_free_to_read=True или книга куплена)",
#         tags=['Book Reading'],
#         responses={
#             200: BookDetailSerializer,
#             403: OpenApiTypes.OBJECT,
#             404: OpenApiTypes.OBJECT
#         }
#     )
#     def get(self, request, *args, **kwargs):
#         slug = kwargs.get('slug')
#         logger.info(f"📖 GET /api/books/{slug}/read/ - Чтение книги")
        
#         book = self.get_object()
        
#         # Проверяем право на чтение
#         if not book.can_read(request.user):
#             return Response(
#                 {'error': 'У вас нет прав для чтения этой книги'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Увеличиваем счетчик просмотров
#         book.update_views()
        
#         # Создаем или обновляем историю чтения
#         try:
#             reader_profile = request.user.reader_profile
#             from core.profiles.models import ReadingHistory
            
#             history, created = ReadingHistory.objects.get_or_create(
#                 reader=reader_profile,
#                 book=book
#             )
            
#             if created:
#                 logger.info(f"✅ Создана история чтения для {request.user.username}")
            
#         except Exception as e:
#             logger.error(f"❌ Ошибка создания истории чтения: {e}")
        
#         serializer = self.get_serializer(book)
#         return Response(serializer.data)


# class BookDownloadView(APIView):
#     """
#     Эндпоинт для скачивания файла книги
#     """
#     permission_classes = [permissions.IsAuthenticated, IsReader]
    
#     @extend_schema(
#         summary="Скачать книгу",
#         description="Скачать файл книги (только если allow_download=True)",
#         tags=['Book Reading'],
#         responses={
#             200: OpenApiTypes.BINARY,
#             403: OpenApiTypes.OBJECT,
#             404: OpenApiTypes.OBJECT
#         }
#     )
#     def get(self, request, slug):
#         logger.info(f"⬇️ GET /api/books/{slug}/download/ - Скачивание книги")
        
#         book = get_object_or_404(Book, slug=slug)
        
#         # Проверяем право на скачивание
#         if not book.can_download(request.user):
#             return Response(
#                 {'error': 'Скачивание этой книги запрещено'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Проверяем наличие файла
#         if not book.file:
#             return Response(
#                 {'error': 'Файл книги отсутствует'},
#                 status=status.HTTP_404_NOT_FOUND
#             )
        
#         # Увеличиваем счетчик скачиваний
#         book.update_downloads()
        
#         logger.info(f"✅ Книга скачана: {book.title}")
        
#         # Возвращаем файл
#         response = FileResponse(
#             book.file.open('rb'),
#             content_type='application/octet-stream'
#         )
#         response['Content-Disposition'] = f'attachment; filename="{book.slug}"'
#         return response


# class BookProgressView(APIView):
#     """
#     Обновление прогресса чтения книги
#     """
#     permission_classes = [permissions.IsAuthenticated, IsReader]
    
#     @extend_schema(
#         summary="Обновить прогресс чтения",
#         description="Отправить текущую страницу для обновления прогресса в истории чтения",
#         tags=['Book Reading'],
#         request=OpenApiTypes.OBJECT,
#         responses={
#             200: OpenApiTypes.OBJECT,
#             403: OpenApiTypes.OBJECT,
#             404: OpenApiTypes.OBJECT
#         }
#     )
#     def post(self, request, slug):
#         logger.info(f"📊 POST /api/books/{slug}/progress/ - Обновление прогресса")
        
#         book = get_object_or_404(Book, slug=slug)
        
#         # Проверяем право на чтение
#         if not book.can_read(request.user):
#             return Response(
#                 {'error': 'У вас нет прав для чтения этой книги'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         current_page = request.data.get('current_page')
        
#         if current_page is None:
#             return Response(
#                 {'error': 'Требуется параметр current_page'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         try:
#             current_page = int(current_page)
#             if current_page < 0:
#                 raise ValueError()
#         except (ValueError, TypeError):
#             return Response(
#                 {'error': 'current_page должен быть положительным числом'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Получаем или создаем историю чтения
#         try:
#             reader_profile = request.user.reader_profile
#             from core.profiles.models import ReadingHistory
            
#             history, created = ReadingHistory.objects.get_or_create(
#                 reader=reader_profile,
#                 book=book
#             )
            
#             # Обновляем прогресс
#             total_pages = book.pages if book.pages > 0 else 1
#             history.update_progress(current_page, total_pages)
            
#             logger.info(f"✅ Прогресс обновлен: {history.progress_percentage}%")
            
#             return Response({
#                 'success': True,
#                 'progress_percentage': history.progress_percentage,
#                 'is_completed': history.is_completed,
#                 'last_page_read': history.last_page_read
#             })
            
#         except Exception as e:
#             logger.error(f"❌ Ошибка обновления прогресса: {e}")
#             return Response(
#                 {'error': str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
