"""
Serializers for user profiles.
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.books.models import Genre
from core.profiles.models import AuthorProfile, ReaderProfile


User = get_user_model()


class ReaderPreferredGenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name', 'slug']
        read_only_fields = fields
        ref_name = 'ReaderPreferredGenre'


class ReaderProfileSerializer(serializers.ModelSerializer):
    preferred_genres = ReaderPreferredGenreSerializer(many=True, read_only=True)
    preferred_genre_ids = serializers.PrimaryKeyRelatedField(
        source='preferred_genres',
        queryset=Genre.objects.all(),
        many=True,
        required=False,
        write_only=True,
    )

    class Meta:
        model = ReaderProfile
        fields = [
            'id',
            'user',
            'avatar',
            'is_active',
            'preferred_genres',
            'preferred_genre_ids',
            'books_read',
            'reviews_written',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['user', 'books_read', 'reviews_written', 'created_at', 'updated_at']
        ref_name = 'ReaderProfile'


class AuthorProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = AuthorProfile
        fields = [
            'id',
            'user',
            'bio',
            'website',
            'telegram',
            'vkontakte',
            'is_approved',
            'requested_at',
            'approved_at',
            'total_views',
            'total_sales',
            'total_donations',
            'full_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'user',
            'total_views',
            'total_sales',
            'total_donations',
            'requested_at',
            'approved_at',
            'created_at',
            'updated_at',
        ]
        ref_name = 'AuthorProfile'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'is_author',
            'email_confirmed',
            'telegram_confirmed',
        ]
        read_only_fields = ['id', 'is_author', 'email_confirmed', 'telegram_confirmed']
        ref_name = 'User'


class UserProfileSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)
    reader_profile = ReaderProfileSerializer(required=False)
    author_profile = AuthorProfileSerializer(required=False, allow_null=True)
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'reader_profile',
            'author_profile',
            'is_author',
            'email_confirmed',
            'telegram_confirmed',
        ]
        read_only_fields = ['id', 'username', 'role', 'is_author', 'email_confirmed', 'telegram_confirmed']
        ref_name = 'UserProfile'

    def update(self, instance, validated_data):
        reader_profile_data = validated_data.pop('reader_profile', None)
        author_profile_data = validated_data.pop('author_profile', None)

        updated_user_fields = []
        for field in ['email', 'first_name', 'last_name']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
                updated_user_fields.append(field)

        if updated_user_fields:
            instance.save(update_fields=updated_user_fields)

        if reader_profile_data is not None:
            reader_profile, _ = ReaderProfile.objects.get_or_create(user=instance)
            preferred_genres = reader_profile_data.pop('preferred_genres', None)

            for attr, value in reader_profile_data.items():
                setattr(reader_profile, attr, value)

            reader_profile.save()

            if preferred_genres is not None:
                reader_profile.preferred_genres.set(preferred_genres)

        if author_profile_data is not None:
            if not hasattr(instance, 'author_profile'):
                raise serializers.ValidationError(
                    {'author_profile': 'Author profile does not exist. Create it first.'}
                )

            author_profile = instance.author_profile
            for attr, value in author_profile_data.items():
                setattr(author_profile, attr, value)
            author_profile.save()

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if not hasattr(User, 'role') or 'role' not in [f.name for f in User._meta.get_fields()]:
            if hasattr(instance, 'is_author') and instance.is_author:
                representation['role'] = 'author'
            elif instance.is_superuser or instance.is_staff:
                representation['role'] = 'admin'
            else:
                representation['role'] = 'reader'

        return representation


class PublicUserProfileSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)
    reader_profile = ReaderProfileSerializer(read_only=True)
    author_profile = AuthorProfileSerializer(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'role',
            'reader_profile',
            'author_profile',
            'is_author',
        ]
        read_only_fields = fields
        ref_name = 'PublicUserProfile'
