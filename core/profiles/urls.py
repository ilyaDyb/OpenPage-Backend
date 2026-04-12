from django.urls import path

from core.profiles.views import (
    CreateAuthorProfileView,
    CreateReaderProfileView,
    CurrentUserProfileView,
    PublicUserProfileView,
    UserByUsernameProfileView,
)


app_name = 'profiles'

urlpatterns = [
    path('', CurrentUserProfileView.as_view(), name='current-user-profile'),
    path('reader/', CreateReaderProfileView.as_view(), name='reader-profile'),
    path('author/', CreateAuthorProfileView.as_view(), name='author-profile'),
    path('username/<str:username>/', UserByUsernameProfileView.as_view(), name='user-profile-by-username'),
    path('<int:pk>/', PublicUserProfileView.as_view(), name='public-user-profile'),
]
