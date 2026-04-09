"""
URL-маршруты для профилей пользователей
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.profiles.views import (
    CurrentUserProfileView,
    PublicUserProfileView,
    UserByUsernameProfileView,
    CreateReaderProfileView,
    CreateAuthorProfileView,
)

app_name = 'profiles'

urlpatterns = [
    path('', CurrentUserProfileView.as_view(), name='current-user-profile'),

    path('<int:pk>/', PublicUserProfileView.as_view(), name='public-user-profile'),
    
    path('<str:username>/', UserByUsernameProfileView.as_view(), name='user-profile-by-username'),
    
    path('reader/', CreateReaderProfileView.as_view(), name='reader-profile'),
    path('author/', CreateAuthorProfileView.as_view(), name='author-profile'),
]
