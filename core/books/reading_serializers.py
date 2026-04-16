"""Serializers for bookmarks, reading history, reviews, and author requests."""
from django.contrib.auth import get_user_model
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.profiles.models import AuthorProfile, Bookmark, ReadingHistory, Review


User = get_user_model()


class BookmarkSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_slug = serializers.CharField(source='book.slug', read_only=True)

    class Meta:
        model = Bookmark
        fields = [
            'id',
            'reader',
            'book',
            'book_title',
            'book_slug',
            'page_number',
            'note',
            'created_at',
        ]
        read_only_fields = ['id', 'reader', 'created_at', 'book_title', 'book_slug']
        ref_name = 'ReadingBookmark'

    def validate_page_number(self, value):
        if value < 1:
            raise serializers.ValidationError('Page number must be greater than 0.')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        book = attrs.get('book') or getattr(self.instance, 'book', None)
        page_number = attrs.get('page_number') or getattr(self.instance, 'page_number', None)

        if book and page_number and book.pages > 0 and page_number > book.pages:
            raise serializers.ValidationError(
                {'page_number': f'Page number cannot exceed the total book pages ({book.pages}).'}
            )

        reader = self.context['request'].user.reader_profile
        if book and page_number:
            queryset = Bookmark.objects.filter(reader=reader, book=book, page_number=page_number)
            if self.instance is not None:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    {'page_number': 'A bookmark for this page already exists.'}
                )

        return attrs

    def create(self, validated_data):
        validated_data['reader'] = self.context['request'].user.reader_profile
        return super().create(validated_data)


class ReadingHistorySerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_slug = serializers.CharField(source='book.slug', read_only=True)
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = ReadingHistory
        fields = [
            'id',
            'reader',
            'book',
            'book_title',
            'book_slug',
            'cover_url',
            'started_at',
            'finished_at',
            'last_page_read',
            'progress_percentage',
            'is_completed',
        ]
        read_only_fields = [
            'id',
            'reader',
            'started_at',
            'finished_at',
            'progress_percentage',
            'is_completed',
            'book_title',
            'book_slug',
            'cover_url',
        ]
        ref_name = 'ReadingHistory'

    @extend_schema_field(OpenApiTypes.URI)
    def get_cover_url(self, obj):
        if not obj.book or not obj.book.cover:
            return None

        request = self.context.get('request')
        return request.build_absolute_uri(obj.book.cover.url) if request else obj.book.cover.url

    def validate_last_page_read(self, value):
        if value < 0:
            raise serializers.ValidationError('Last page read cannot be negative.')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        book = attrs.get('book') or getattr(self.instance, 'book', None)
        last_page_read = attrs.get('last_page_read')

        if book and last_page_read is not None and book.pages > 0 and last_page_read > book.pages:
            raise serializers.ValidationError(
                {'last_page_read': f'Last page read cannot exceed the total book pages ({book.pages}).'}
            )

        if self.instance is None and book and not self.context.get('allow_existing_history', False):
            reader = self.context['request'].user.reader_profile
            if ReadingHistory.objects.filter(reader=reader, book=book).exists():
                raise serializers.ValidationError({'book': 'Reading history for this book already exists.'})

        return attrs

    def create(self, validated_data):
        validated_data['reader'] = self.context['request'].user.reader_profile
        history = super().create(validated_data)
        if history.last_page_read:
            total_pages = history.book.pages if history.book and history.book.pages > 0 else 1
            history.update_progress(history.last_page_read, total_pages)
        return history

    def update(self, instance, validated_data):
        last_page_read = validated_data.get('last_page_read')
        if last_page_read is not None:
            total_pages = instance.book.pages if instance.book and instance.book.pages > 0 else 1
            instance.update_progress(last_page_read, total_pages)
            return instance

        return super().update(instance, validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    reader_name = serializers.CharField(source='reader.user.username', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_slug = serializers.CharField(source='book.slug', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id',
            'reader',
            'reader_name',
            'book',
            'book_title',
            'book_slug',
            'rating',
            'text',
            'is_verified_purchase',
            'helpful_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'reader',
            'reader_name',
            'book_title',
            'book_slug',
            'is_verified_purchase',
            'helpful_count',
            'created_at',
            'updated_at',
        ]
        ref_name = 'ReadingReview'


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['book', 'rating', 'text']
        ref_name = 'ReviewCreate'

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating must be between 1 and 5.')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        reader = self.context['request'].user.reader_profile
        book = attrs.get('book')

        queryset = Review.objects.filter(reader=reader, book=book)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError({'book': 'You have already reviewed this book.'})

        return attrs

    def create(self, validated_data):
        validated_data['reader'] = self.context['request'].user.reader_profile
        validated_data['is_verified_purchase'] = False
        review = super().create(validated_data)
        reader = review.reader
        reader.reviews_written = Review.objects.filter(reader=reader).count()
        reader.save(update_fields=['reviews_written'])
        return review


class AuthorRequestSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = AuthorProfile
        fields = [
            'id',
            'username',
            'email',
            'full_name',
            'bio',
            'website',
            'telegram',
            'vkontakte',
            'is_approved',
            'requested_at',
            'approved_at',
        ]
        read_only_fields = fields
        ref_name = 'AuthorRequest'


class AuthorRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorProfile
        fields = ['bio', 'website', 'telegram', 'vkontakte']
        ref_name = 'AuthorRequestCreate'


class AuthorRequestModerationSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    rejection_reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)
