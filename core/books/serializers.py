"""Serializers for books and genres."""
from pathlib import Path

from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.books.models import Book, BookStatus, Genre
from core.books.permissions import is_moderator_or_staff
from core.profiles.models import AuthorProfile
from core.profiles.serializers import AuthorProfileSerializer


ALLOWED_COVER_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_BOOK_FILE_EXTENSIONS = {'.pdf', '.epub', '.fb2', '.txt'}


class GenreSerializer(serializers.ModelSerializer):
    books_count = serializers.SerializerMethodField()

    class Meta:
        model = Genre
        fields = ['id', 'name', 'slug', 'description', 'created_at', 'books_count']
        read_only_fields = ['id', 'created_at', 'books_count']
        ref_name = 'Genre'

    @extend_schema_field(OpenApiTypes.INT)
    def get_books_count(self, obj):
        return obj.books.filter(status='published', is_active=True).count()

    def validate_slug(self, value):
        return validate_unique_slug(Genre, value, self.instance)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        slug_candidate = attrs.get('slug') or attrs.get('name')
        if slug_candidate:
            validate_unique_slug(Genre, slug_candidate, self.instance)
        return attrs


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
    read_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'slug',
            'authors',
            'genres',
            'cover_url',
            'read_url',
            'download_url',
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

    @extend_schema_field(OpenApiTypes.URI)
    def get_read_url(self, obj):
        request = self.context.get('request')
        return build_book_action_url(
            request,
            'reading:book-read',
            obj.slug,
            can_access=can_user_read_book(request, obj),
        )

    @extend_schema_field(OpenApiTypes.URI)
    def get_download_url(self, obj):
        request = self.context.get('request')
        return build_book_action_url(
            request,
            'reading:book-download',
            obj.slug,
            can_access=can_user_download_file(request, obj),
        )


class BookDetailSerializer(serializers.ModelSerializer):
    authors = AuthorProfileSerializer(many=True, read_only=True)
    genres = GenreSimpleSerializer(many=True, read_only=True)
    cover_url = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    read_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
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
            'read_url',
            'download_url',
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

        include_file_url = self.context.get('include_file_url', False)
        if not include_file_url:
            return None

        request = self.context.get('request')
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url

    @extend_schema_field(OpenApiTypes.URI)
    def get_read_url(self, obj):
        request = self.context.get('request')
        return build_book_action_url(
            request,
            'reading:book-read',
            obj.slug,
            can_access=can_user_read_book(request, obj),
        )

    @extend_schema_field(OpenApiTypes.URI)
    def get_download_url(self, obj):
        request = self.context.get('request')
        return build_book_action_url(
            request,
            'reading:book-download',
            obj.slug,
            can_access=can_user_download_file(request, obj),
        )


class BookCreateUpdateSerializer(serializers.ModelSerializer):
    author_ids = serializers.PrimaryKeyRelatedField(
        queryset=AuthorProfile.objects.filter(is_approved=True),
        many=True,
        required=False,
        write_only=True,
        source='authors',
    )
    genre_ids = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(),
        many=True,
        required=False,
        write_only=True,
        source='genres',
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

    def validate_slug(self, value):
        return validate_unique_slug(Book, value, self.instance)

    def validate_cover(self, value):
        validate_uploaded_extension(value, ALLOWED_COVER_EXTENSIONS, 'cover')
        validate_uploaded_size(value, settings.MAX_COVER_UPLOAD_SIZE, 'cover')
        return value

    def validate_file(self, value):
        validate_uploaded_extension(value, ALLOWED_BOOK_FILE_EXTENSIONS, 'file')
        validate_uploaded_size(value, settings.MAX_BOOK_UPLOAD_SIZE, 'file')
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Price cannot be negative.')
        return value

    def validate_pages(self, value):
        if value < 0:
            raise serializers.ValidationError('Pages cannot be negative.')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context['request']
        try:
            current_author = request.user.author_profile
        except Exception:
            current_author = None
        authors = attrs.get('authors')
        slug_candidate = attrs.get('slug') or attrs.get('title')
        book_file = attrs.get('file', getattr(self.instance, 'file', None))
        allow_download = attrs.get('allow_download', getattr(self.instance, 'allow_download', False))
        status_value = attrs.get('status', getattr(self.instance, 'status', None))

        if slug_candidate:
            validate_unique_slug(Book, slug_candidate, self.instance)

        if authors is not None and current_author and not is_staff_or_moderator(request.user):
            if current_author not in authors:
                raise serializers.ValidationError(
                    {'author_ids': 'Current author must remain attached to the book.'}
                )

        if attrs.get('is_free') and attrs.get('price', getattr(self.instance, 'price', 0)) not in (0, 0.0):
            raise serializers.ValidationError({'price': 'Free books must have price 0.'})

        if allow_download and not book_file:
            raise serializers.ValidationError({'file': 'Book file is required when download is enabled.'})

        if status_value == BookStatus.PUBLISHED and not book_file:
            raise serializers.ValidationError({'file': 'Published books must include a book file.'})

        return attrs


def validate_unique_slug(model_class, value, instance=None):
    if not value:
        return value

    normalized = slugify(value)
    if not normalized:
        raise serializers.ValidationError('Slug is invalid.')

    queryset = model_class.objects.filter(slug=normalized)
    if instance is not None:
        queryset = queryset.exclude(pk=instance.pk)

    if queryset.exists():
        raise serializers.ValidationError('Slug must be unique.')

    return normalized


def validate_uploaded_extension(value, allowed_extensions, field_name):
    extension = Path(value.name).suffix.lower()
    if extension not in allowed_extensions:
        raise serializers.ValidationError(
            f'Unsupported {field_name} format. Allowed: {", ".join(sorted(allowed_extensions))}.'
        )


def validate_uploaded_size(value, max_size, field_name):
    if value.size > max_size:
        raise serializers.ValidationError(
            f'{field_name.capitalize()} is too large. Maximum size is {max_size // (1024 * 1024)} MB.'
        )


def is_staff_or_moderator(user):
    return (
        user.is_staff
        or user.is_superuser
        or getattr(user, 'role', None) in {'moderator', 'admin'}
    )


def build_book_action_url(request, viewname, slug, can_access):
    if not request or not can_access:
        return None
    return request.build_absolute_uri(reverse(viewname, kwargs={'slug': slug}))


def can_user_read_book(request, book):
    if not request or not request.user.is_authenticated:
        return False

    user = request.user
    if is_moderator_or_staff(user):
        return True

    if book.authors.filter(user=user).exists():
        return True

    return book.can_read(user)


def can_user_download_file(request, book):
    if not request or not request.user.is_authenticated or not book.file:
        return False

    user = request.user
    if is_moderator_or_staff(user):
        return True

    if book.authors.filter(user=user).exists():
        return True

    return book.can_download(user)
