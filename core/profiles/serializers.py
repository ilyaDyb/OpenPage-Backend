"""
Сериализаторы для профилей пользователей
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.profiles.models import AuthorProfile, ReaderProfile

User = get_user_model()


class ReaderProfileSerializer(serializers.ModelSerializer):
    """Сериализатор профиля читателя"""
    # preferred_genres и preferred_genres_ids отключены пока books app не подключен
    
    class Meta:
        model = ReaderProfile
        fields = [
            'id', 'user', 'avatar', 'is_active',
            'books_read', 'reviews_written',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'books_read', 'reviews_written', 'created_at', 'updated_at']
        ref_name = 'ReaderProfile'


class AuthorProfileSerializer(serializers.ModelSerializer):
    """Сериализатор профиля автора"""
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = AuthorProfile
        fields = [
            'id', 'user', 'bio', 'website', 'telegram', 'vkontakte',
            'is_approved', 'requested_at', 'approved_at',
            'total_views', 'total_sales', 'total_donations',
            'full_name', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'user', 'total_views', 'total_sales', 'total_donations',
            'requested_at', 'approved_at', 'created_at', 'updated_at'
        ]
        ref_name = 'AuthorProfile'


class UserSerializer(serializers.ModelSerializer):
    """Базовый сериализатор пользователя"""
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'is_author', 'email_confirmed', 'telegram_confirmed'
        ]
        read_only_fields = ['id', 'is_author', 'email_confirmed', 'telegram_confirmed']
        ref_name = 'User'


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Комбинированный сериализатор профиля пользователя
    Включает данные User, ReaderProfile и AuthorProfile
    """
    # Поля из User
    role = serializers.CharField(read_only=True)
    
    # Вложенные профили
    reader_profile = ReaderProfileSerializer(read_only=True)
    author_profile = AuthorProfileSerializer(read_only=True, allow_null=True)
    
    # Поля для обновления User
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'reader_profile', 'author_profile',
            'is_author', 'email_confirmed', 'telegram_confirmed'
        ]
        read_only_fields = ['id', 'username', 'role', 'is_author', 'email_confirmed', 'telegram_confirmed']
        ref_name = 'UserProfile'
    
    def update(self, instance, validated_data):
        """
        Обновление данных пользователя и связанных профилей
        """
        # Обновляем поля User
        user_fields = ['email', 'first_name', 'last_name']
        for field in user_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        
        instance.save(update_fields=user_fields)
        
        return instance
    
    def to_representation(self, instance):
        """Добавляем вычисляемое поле role если его нет в модели"""
        representation = super().to_representation(instance)
        
        # Если в модели нет поля role, вычисляем его
        if not hasattr(User, 'role') or 'role' not in [f.name for f in User._meta.get_fields()]:
            if hasattr(instance, 'is_author') and instance.is_author:
                representation['role'] = 'author'
            elif instance.is_superuser or instance.is_staff:
                representation['role'] = 'admin'
            else:
                representation['role'] = 'reader'
        
        return representation
