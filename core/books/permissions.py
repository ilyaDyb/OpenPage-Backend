"""
Permission classes для ограничения доступа
"""
from rest_framework import permissions
from core.profiles.models import AuthorProfile


class IsOwner(permissions.BasePermission):
    """
    Проверка, что объект принадлежит текущему пользователю
    Используется для закладок, отзывов, истории чтения
    """
    
    def has_object_permission(self, request, view, obj):
        # Разрешаем безопасные методы (GET, HEAD, OPTIONS) всем авторизованным
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Для остальных методов проверяем владение
        if hasattr(obj, 'reader'):
            return obj.reader.user == request.user
        
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsAuthor(permissions.BasePermission):
    """
    Проверка, что пользователь имеет подтвержденный профиль автора
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Проверяем наличие профиля автора и его подтверждение
        try:
            author_profile = request.user.author_profile
            return author_profile.is_approved
        except AuthorProfile.DoesNotExist:
            return False


class IsModerator(permissions.BasePermission):
    """
    Проверка, что пользователь имеет роль модератора или администратора
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        user = request.user
        
        # Проверяем роль пользователя
        if hasattr(user, 'role'):
            return user.role in ['moderator', 'admin']
        
        # Fallback: проверяем через is_staff/is_superuser
        return user.is_staff or user.is_superuser


class IsReader(permissions.BasePermission):
    """
    Проверка, что пользователь имеет профиль читателя
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            _ = request.user.reader_profile
            return True
        except Exception:
            return False


class IsAuthorOrModerator(permissions.BasePermission):
    """
    Проверка: автор ИЛИ модератор
    Используется для модерации книг
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Проверяем модератора
        if hasattr(request.user, 'role') and request.user.role in ['moderator', 'admin']:
            return True
        
        # Проверяем автора
        try:
            return request.user.author_profile.is_approved
        except Exception:
            return False
