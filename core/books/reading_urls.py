"""URL routes for reading features."""
from django.urls import path

from core.books.reading_api import BookDownloadView, BookProgressView, BookReadView
from core.books.reading_views import (
    AuthorRequestModerateView,
    AuthorRequestView,
    AuthorRequestsListView,
    BookmarkCreateView,
    BookmarkDeleteView,
    BookmarkListView,
    ReadingHistoryCreateView,
    ReadingHistoryListView,
    ReadingHistoryUpdateView,
    ReviewCreateView,
    ReviewDeleteView,
    ReviewDetailView,
    ReviewHelpfulView,
    ReviewListView,
)


app_name = 'reading'


urlpatterns = [
    path('books/<str:slug>/read/', BookReadView.as_view(), name='book-read'),
    path('books/<str:slug>/download/', BookDownloadView.as_view(), name='book-download'),
    path('books/<str:slug>/progress/', BookProgressView.as_view(), name='book-progress'),

    path('bookmarks/', BookmarkListView.as_view(), name='bookmark-list'),
    path('bookmarks/create/', BookmarkCreateView.as_view(), name='bookmark-create'),
    path('bookmarks/<uuid:pk>/delete/', BookmarkDeleteView.as_view(), name='bookmark-delete'),

    path('reading-history/', ReadingHistoryListView.as_view(), name='reading-history-list'),
    path('reading-history/create/', ReadingHistoryCreateView.as_view(), name='reading-history-create'),
    path('reading-history/<uuid:pk>/update/', ReadingHistoryUpdateView.as_view(), name='reading-history-update'),

    path('reviews/', ReviewListView.as_view(), name='review-list'),
    path('reviews/create/', ReviewCreateView.as_view(), name='review-create'),
    path('reviews/<uuid:pk>/', ReviewDetailView.as_view(), name='review-detail'),
    path('reviews/<uuid:pk>/helpful/', ReviewHelpfulView.as_view(), name='review-helpful'),
    path('reviews/<uuid:pk>/delete/', ReviewDeleteView.as_view(), name='review-delete'),

    path('author/request/', AuthorRequestView.as_view(), name='author-request'),
    path('author/requests/', AuthorRequestsListView.as_view(), name='author-requests-list'),
    path('author/requests/<int:pk>/moderate/', AuthorRequestModerateView.as_view(), name='author-request-moderate'),
]
