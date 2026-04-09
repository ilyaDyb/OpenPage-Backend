# """
# URL-маршруты для функций чтения (закладки, история, отзывы)
# """
# from django.urls import path
# from core.books.reading_views import (
#     # Bookmarks
#     BookmarkListView,
#     BookmarkCreateView,
#     BookmarkDeleteView,
    
#     # Reading History
#     ReadingHistoryListView,
#     ReadingHistoryCreateView,
#     ReadingHistoryUpdateView,
    
#     # Reviews
#     ReviewListView,
#     ReviewCreateView,
#     ReviewDetailView,
#     ReviewHelpfulView,
#     ReviewDeleteView,
    
#     # Author Requests
#     AuthorRequestView,
#     AuthorRequestsListView,
#     AuthorRequestModerateView,
# )
# from core.books.reading_api import (
#     BookReadView,
#     BookDownloadView,
#     BookProgressView,
# )

# app_name = 'reading'

# urlpatterns = [
#     # Book Reading
#     path('books/<str:slug>/read/', BookReadView.as_view(), name='book-read'),
#     path('books/<str:slug>/download/', BookDownloadView.as_view(), name='book-download'),
#     path('books/<str:slug>/progress/', BookProgressView.as_view(), name='book-progress'),
    
#     # Bookmarks
#     path('bookmarks/', BookmarkListView.as_view(), name='bookmark-list'),
#     path('bookmarks/create/', BookmarkCreateView.as_view(), name='bookmark-create'),
#     path('bookmarks/<uuid:pk>/delete/', BookmarkDeleteView.as_view(), name='bookmark-delete'),
    
#     # Reading History
#     path('reading-history/', ReadingHistoryListView.as_view(), name='reading-history-list'),
#     path('reading-history/create/', ReadingHistoryCreateView.as_view(), name='reading-history-create'),
#     path('reading-history/<uuid:pk>/update/', ReadingHistoryUpdateView.as_view(), name='reading-history-update'),
    
#     # Reviews
#     path('reviews/', ReviewListView.as_view(), name='review-list'),
#     path('reviews/create/', ReviewCreateView.as_view(), name='review-create'),
#     path('reviews/<uuid:pk>/', ReviewDetailView.as_view(), name='review-detail'),
#     path('reviews/<uuid:pk>/helpful/', ReviewHelpfulView.as_view(), name='review-helpful'),
#     path('reviews/<uuid:pk>/delete/', ReviewDeleteView.as_view(), name='review-delete'),
    
#     # Author Requests
#     path('author/request/', AuthorRequestView.as_view(), name='author-request'),
#     path('author/requests/', AuthorRequestsListView.as_view(), name='author-requests-list'),
#     path('author/requests/<uuid:pk>/moderate/', AuthorRequestModerateView.as_view(), name='author-request-moderate'),
# ]