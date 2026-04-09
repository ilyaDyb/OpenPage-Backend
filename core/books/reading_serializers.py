# """
# Сериализаторы для закладок, истории чтения и отзывов
# """
# from rest_framework import serializers
# from django.utils import timezone
# from core.profiles.models import Bookmark, ReadingHistory, Review


# class BookmarkSerializer(serializers.ModelSerializer):
#     """Сериализатор закладки"""
#     book_title = serializers.CharField(source='book.title', read_only=True)
    
#     class Meta:
#         model = Bookmark
#         fields = ['id', 'reader', 'book', 'book_title', 'page_number', 'note', 'created_at']
#         read_only_fields = ['id', 'reader', 'created_at']
#         ref_name = 'Bookmark'
    
#     def validate_page_number(self, value):
#         """Проверка номера страницы"""
#         if value < 1:
#             raise serializers.ValidationError("Номер страницы должен быть больше 0")
#         return value
    
#     def validate(self, data):
#         """Дополнительная проверка: страница не превышает количество страниц книги"""
#         book = data.get('book')
#         page_number = data.get('page_number')
        
#         if book and page_number and book.pages > 0:
#             if page_number > book.pages:
#                 raise serializers.ValidationError(
#                     f"Номер страницы ({page_number}) превышает количество страниц в книге ({book.pages})"
#                 )
        
#         return data
    
#     def create(self, validated_data):
#         """Создание закладки с автоматическим указанием читателя"""
#         validated_data['reader'] = self.context['request'].user.reader_profile
#         return super().create(validated_data)


# class ReadingHistorySerializer(serializers.ModelSerializer):
#     """Сериализатор истории чтения"""
#     book_title = serializers.CharField(source='book.title', read_only=True)
#     cover_url = serializers.SerializerMethodField()
    
#     class Meta:
#         model = ReadingHistory
#         fields = [
#             'id', 'reader', 'book', 'book_title', 'cover_url',
#             'started_at', 'finished_at', 'last_page_read',
#             'progress_percentage', 'is_completed'
#         ]
#         read_only_fields = ['id', 'reader', 'started_at']
#         ref_name = 'ReadingHistory'
    
#     def get_cover_url(self, obj):
#         """Получить URL обложки книги"""
#         if obj.book.cover:
#             request = self.context.get('request')
#             if request:
#                 return request.build_absolute_uri(obj.book.cover.url)
#             return obj.book.cover.url
#         return None
    
#     def validate_last_page_read(self, value):
#         """Проверка номера страницы"""
#         if value < 0:
#             raise serializers.ValidationError("Номер страницы не может быть отрицательным")
#         return value
    
#     def update(self, instance, validated_data):
#         """Обновление прогресса чтения"""
#         last_page_read = validated_data.get('last_page_read')
        
#         if last_page_read is not None:
#             # Вызываем метод модели для обновления прогресса
#             total_pages = instance.book.pages if instance.book.pages > 0 else 1
#             instance.update_progress(last_page_read, total_pages)
#         else:
#             # Стандартное обновление
#             for attr, value in validated_data.items():
#                 setattr(instance, attr, value)
#             instance.save()
        
#         return instance
    
#     def create(self, validated_data):
#         """Создание записи истории чтения"""
#         validated_data['reader'] = self.context['request'].user.reader_profile
        
#         # Проверяем, существует ли уже запись для этой книги
#         existing = ReadingHistory.objects.filter(
#             reader=validated_data['reader'],
#             book=validated_data['book']
#         ).first()
        
#         if existing:
#             return existing
        
#         return super().create(validated_data)


# class ReviewSerializer(serializers.ModelSerializer):
#     """Сериализатор отзыва"""
#     reader_name = serializers.CharField(source='reader.user.username', read_only=True)
#     book_title = serializers.CharField(source='book.title', read_only=True)
#     is_verified_purchase = serializers.BooleanField(read_only=True, default=False)
    
#     class Meta:
#         model = Review
#         fields = [
#             'id', 'reader', 'reader_name', 'book', 'book_title',
#             'rating', 'text', 'is_verified_purchase', 'helpful_count',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'reader', 'is_verified_purchase', 'helpful_count', 'created_at', 'updated_at']
#         ref_name = 'Review'
    
#     def validate_rating(self, value):
#         """Проверка рейтинга"""
#         if value < 1 or value > 5:
#             raise serializers.ValidationError("Рейтинг должен быть от 1 до 5")
#         return value
    
#     def validate(self, data):
#         """Проверка уникальности отзыва"""
#         book = data.get('book')
#         reader = self.context['request'].user.reader_profile
        
#         # Проверяем, нет ли уже отзыва от этого читателя на эту книгу
#         existing_review = Review.objects.filter(reader=reader, book=book).first()
        
#         if existing_review and self.instance != existing_review:
#             raise serializers.ValidationError("Вы уже оставили отзыв на эту книгу")
        
#         return data
    
#     def create(self, validated_data):
#         """Создание отзыва"""
#         validated_data['reader'] = self.context['request'].user.reader_profile
        
#         # Проверяем покупку или чтение (упрощенно - всегда False для начала)
#         # В реальности здесь должна быть логика проверки покупки
#         validated_data['is_verified_purchase'] = self._check_verified_purchase(
#             validated_data['reader'],
#             validated_data['book']
#         )
        
#         return super().create(validated_data)
    
#     def _check_verified_purchase(self, reader, book):
#         """
#         Проверка, купил ли пользователь книгу
#         TODO: Реализовать проверку через систему покупок
#         """
#         # Пока возвращаем False
#         # В будущем: проверять через Order模型
#         return False


# class ReviewCreateSerializer(serializers.ModelSerializer):
#     """Сериализатор для создания отзыва (расширенный)"""
#     class Meta:
#         model = Review
#         fields = ['book', 'rating', 'text']
#         write_only_fields = ['book', 'rating', 'text']
