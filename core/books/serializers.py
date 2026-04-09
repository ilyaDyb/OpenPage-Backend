# """
# Сериализаторы для книг и жанров
# """
# from rest_framework import serializers
# from core.books.models import Genre, Book
# from core.profiles.serializers import AuthorProfileSerializer


# class GenreSerializer(serializers.ModelSerializer):
#     """Сериализатор жанра"""
#     books_count = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Genre
#         fields = ['id', 'name', 'slug', 'description', 'created_at', 'books_count']
#         read_only_fields = ['id', 'slug', 'created_at']
#         ref_name = 'Genre'
    
#     def get_books_count(self, obj):
#         """Получить количество книг в жанре"""
#         return obj.books.filter(status='published', is_active=True).count()


# class GenreSimpleSerializer(serializers.ModelSerializer):
#     """Упрощенный сериализатор жанра для списков"""
#     class Meta:
#         model = Genre
#         fields = ['id', 'name', 'slug']
#         read_only_fields = ['id']
#         ref_name = 'GenreSimple'


# class BookListSerializer(serializers.ModelSerializer):
#     """Сериализатор для списка книг"""
#     authors = serializers.StringRelatedField(many=True, read_only=True)
#     genres = GenreSimpleSerializer(many=True, read_only=True)
#     cover_url = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Book
#         fields = [
#             'id', 'title', 'slug', 'authors', 'genres',
#             'cover_url', 'price', 'is_free', 'pages',
#             'views_count', 'downloads_count', 'status',
#             'is_active', 'created_at'
#         ]
#         read_only_fields = ['id', 'slug', 'created_at']
#         ref_name = 'BookList'
    
#     def get_cover_url(self, obj):
#         """Получить URL обложки"""
#         if obj.cover:
#             request = self.context.get('request')
#             if request:
#                 return request.build_absolute_uri(obj.cover.url)
#             return obj.cover.url
#         return None


# class BookDetailSerializer(serializers.ModelSerializer):
#     """Сериализатор для детального просмотра книги"""
#     authors = AuthorProfileSerializer(many=True, read_only=True)
#     genres = GenreSimpleSerializer(many=True, read_only=True)
#     cover_url = serializers.SerializerMethodField()
#     file_url = serializers.SerializerMethodField()
#     authors_list = serializers.CharField(read_only=True)
#     display_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
#     class Meta:
#         model = Book
#         fields = [
#             'id', 'title', 'slug', 'authors', 'authors_list', 'genres',
#             'description', 'cover_url', 'file_url',
#             'price', 'is_free', 'display_price', 'pages', 'published_at',
#             'views_count', 'downloads_count', 'status', 'is_active',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'slug', 'views_count', 'downloads_count', 'created_at', 'updated_at']
#         ref_name = 'BookDetail'
    
#     def get_cover_url(self, obj):
#         """Получить URL обложки"""
#         if obj.cover:
#             request = self.context.get('request')
#             if request:
#                 return request.build_absolute_uri(obj.cover.url)
#             return obj.cover.url
#         return None
    
#     def get_file_url(self, obj):
#         """Получить URL файла книги"""
#         if obj.file:
#             request = self.context.get('request')
#             if request:
#                 return request.build_absolute_uri(obj.file.url)
#             return obj.file.url
#         return None


# class BookCreateUpdateSerializer(serializers.ModelSerializer):
#     """Сериализатор для создания и обновления книги"""
#     author_ids = serializers.PrimaryKeyRelatedField(
#         queryset=[],
#         many=True,
#         write_only=True,
#         source='authors',
#         help_text='ID авторов (профилей)'
#     )
#     genre_ids = serializers.PrimaryKeyRelatedField(
#         queryset=[],
#         many=True,
#         required=False,
#         write_only=True,
#         source='genres',
#         help_text='ID жанров'
#     )
    
#     class Meta:
#         model = Book
#         fields = [
#             'title', 'slug', 'author_ids', 'description', 'genre_ids',
#             'cover', 'file', 'price', 'is_free', 'pages', 'published_at',
#             'status', 'is_active'
#         ]
#         ref_name = 'BookCreateUpdate'
    
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Устанавливаем queryset динамически
#         try:
#             from core.profiles.models import AuthorProfile
#             self.fields['author_ids'].child_relation.queryset = AuthorProfile.objects.filter(is_approved=True)
#         except Exception:
#             pass
        
#         try:
#             from core.books.models import Genre
#             self.fields['genre_ids'].child_relation.queryset = Genre.objects.all()
#         except Exception:
#             pass
    
#     def create(self, validated_data):
#         """Создание книги"""
#         authors = validated_data.pop('authors', [])
#         genres = validated_data.pop('genres', [])
        
#         book = Book.objects.create(**validated_data)
#         book.authors.set(authors)
#         if genres:
#             book.genres.set(genres)
        
#         return book
    
#     def update(self, instance, validated_data):
#         """Обновление книги"""
#         authors = validated_data.pop('authors', None)
#         genres = validated_data.pop('genres', None)
        
#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)
        
#         instance.save()
        
#         if authors is not None:
#             instance.authors.set(authors)
#         if genres is not None:
#             instance.genres.set(genres)
        
#         return instance
    
#     def validate_price(self, value):
#         """Проверка цены"""
#         if value < 0:
#             raise serializers.ValidationError("Цена не может быть отрицательной")
#         return value
    
#     def validate_pages(self, value):
#         """Проверка количества страниц"""
#         if value < 0:
#             raise serializers.ValidationError("Количество страниц не может быть отрицательным")
#         return value
