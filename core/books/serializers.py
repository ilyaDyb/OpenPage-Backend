"""Сериализаторы для книг и жанров."""
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from core.books.models import Book, Genre
from core.profiles.models import AuthorProfile
from core.profiles.serializers import AuthorProfileSerializer


class GenreSerializer(serializers.ModelSerializer):
    books_count = serializers.SerializerMethodField()

    class Meta:
        model = Genre
        fields = ['id', 'name', 'slug', 'description', 'created_at', 'books_count']
        read_only_fields = ['id', 'slug', 'created_at']
        ref_name = 'Genre'

    @extend_schema_field(OpenApiTypes.INT)
    def get_books_count(self, obj):
        return obj.books.filter(status='published', is_active=True).count()


class GenreSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name', 'slug']
        read_only_fields = ['id', 'slug']
        ref_name = 'GenreSimple'


class BookListSerializer(serializers.ModelSerializer):
    authors = serializers.StringRelatedField(many=True, read_only=True)
    genres = GenreSimpleSerializer(many=True, read_only=True)
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'slug',
            'authors',
            'genres',
            'cover_url',
            'price',
            'is_free',
            'is_free_to_read',
            'allow_download',
            'pages',
            'views_count',
            'downloads_count',
            'status',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at']
        ref_name = 'BookList'

    @extend_schema_field(OpenApiTypes.URI)
    def get_cover_url(self, obj):
        if not obj.cover:
            return None

        request = self.context.get('request')
        return request.build_absolute_uri(obj.cover.url) if request else obj.cover.url


class BookDetailSerializer(serializers.ModelSerializer):
    authors = AuthorProfileSerializer(many=True, read_only=True)
    genres = GenreSimpleSerializer(many=True, read_only=True)
    cover_url = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    authors_list = serializers.CharField(read_only=True)
    display_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'slug',
            'authors',
            'authors_list',
            'genres',
            'description',
            'cover_url',
            'file_url',
            'price',
            'is_free',
            'is_free_to_read',
            'allow_download',
            'display_price',
            'pages',
            'published_at',
            'views_count',
            'downloads_count',
            'status',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'views_count', 'downloads_count', 'created_at', 'updated_at']
        ref_name = 'BookDetail'

    @extend_schema_field(OpenApiTypes.URI)
    def get_cover_url(self, obj):
        if not obj.cover:
            return None

        request = self.context.get('request')
        return request.build_absolute_uri(obj.cover.url) if request else obj.cover.url

    @extend_schema_field(OpenApiTypes.URI)
    def get_file_url(self, obj):
        if not obj.file:
            return None

        request = self.context.get('request')
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class BookCreateUpdateSerializer(serializers.ModelSerializer):
    author_ids = serializers.PrimaryKeyRelatedField(
        queryset=AuthorProfile.objects.filter(is_approved=True),
        many=True,
        required=False,
        write_only=True,
        source='authors',
        help_text='ID авторов (профилей)',
    )
    genre_ids = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(),
        many=True,
        required=False,
        write_only=True,
        source='genres',
        help_text='ID жанров',
    )

    class Meta:
        model = Book
        fields = [
            'title',
            'slug',
            'author_ids',
            'description',
            'genre_ids',
            'cover',
            'file',
            'price',
            'is_free',
            'is_free_to_read',
            'allow_download',
            'pages',
            'published_at',
            'status',
            'is_active',
        ]
        ref_name = 'BookCreateUpdate'

    def create(self, validated_data):
        authors = validated_data.pop('authors', [])
        genres = validated_data.pop('genres', [])

        book = Book.objects.create(**validated_data)
        if authors:
            book.authors.set(authors)
        if genres:
            book.genres.set(genres)

        return book

    def update(self, instance, validated_data):
        authors = validated_data.pop('authors', None)
        genres = validated_data.pop('genres', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if authors is not None:
            instance.authors.set(authors)
        if genres is not None:
            instance.genres.set(genres)

        return instance

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Цена не может быть отрицательной')
        return value

    def validate_pages(self, value):
        if value < 0:
            raise serializers.ValidationError('Количество страниц не может быть отрицательным')
        return value
