from django.urls import path

from core.profiles.views import (
    AuthorSubscriptionListView,
    AuthorSubscriptionView,
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
    path('author-subscriptions/', AuthorSubscriptionListView.as_view(), name='author-subscription-list'),
    path('authors/<int:pk>/subscription/', AuthorSubscriptionView.as_view(), name='author-subscription'),
    path('username/<str:username>/', UserByUsernameProfileView.as_view(), name='user-profile-by-username'),
    path('<int:pk>/', PublicUserProfileView.as_view(), name='public-user-profile'),
]
