from rest_framework import permissions

from core.books.models import BookStatus


def is_moderator_or_staff(user):
    return (
        user.is_staff
        or user.is_superuser
        or getattr(user, 'role', None) in {'moderator', 'admin'}
    )


def get_author_profile(user):
    try:
        return user.author_profile
    except Exception:
        return None


def has_reader_profile(user):
    try:
        return user.reader_profile is not None
    except Exception:
        return False


class IsModeratorOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return is_moderator_or_staff(request.user)


class IsApprovedAuthor(permissions.BasePermission):
    message = 'Only approved authors can perform this action.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        author_profile = get_author_profile(request.user)
        return bool(author_profile and author_profile.is_approved)


class HasAuthorProfile(permissions.BasePermission):
    message = 'Author profile is required.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return get_author_profile(request.user) is not None


class IsBookAuthorOrStaff(permissions.BasePermission):
    message = 'You are not allowed to modify this book.'

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if is_moderator_or_staff(request.user):
            return True

        return obj.authors.filter(user=request.user).exists()


class CanViewBook(permissions.BasePermission):
    message = 'This book is not available.'

    def has_object_permission(self, request, view, obj):
        if obj.status == BookStatus.PUBLISHED and obj.is_active:
            return True

        if not request.user.is_authenticated:
            return False

        if is_moderator_or_staff(request.user):
            return True

        return obj.authors.filter(user=request.user).exists()


class IsReader(permissions.BasePermission):
    message = 'Reader profile is required.'

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and has_reader_profile(request.user))


class IsOwner(permissions.BasePermission):
    message = 'You do not own this object.'

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if is_moderator_or_staff(request.user):
            return True

        if hasattr(obj, 'reader') and obj.reader:
            return obj.reader.user_id == request.user.id

        if hasattr(obj, 'user') and obj.user:
            return obj.user_id == request.user.id

        return False
