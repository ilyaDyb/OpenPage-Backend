from django.urls import path

from core.books.views import (
    BookBySlugView,
    BookCommentDeleteView,
    BookCommentDetailView,
    BookCommentListCreateView,
    BookCreateView,
    BookDeleteView,
    BookDetailView,
    BookLikeView,
    BookListView,
    BookUpdateView,
    GenreDetailView,
    GenreListCreateView,
    MyBooksView,
)


app_name = 'books'

urlpatterns = [
    path('genres/', GenreListCreateView.as_view(), name='genre-list'),
    path('genres/<uuid:pk>/', GenreDetailView.as_view(), name='genre-detail'),
    path('', BookListView.as_view(), name='book-list'),
    path('<uuid:pk>/', BookDetailView.as_view(), name='book-detail'),
    path('slug/<str:slug>/', BookBySlugView.as_view(), name='book-by-slug'),
    path('create/', BookCreateView.as_view(), name='book-create'),
    path('<uuid:pk>/like/', BookLikeView.as_view(), name='book-like'),
    path('<uuid:pk>/comments/', BookCommentListCreateView.as_view(), name='book-comment-list'),
    path('comments/<uuid:pk>/', BookCommentDetailView.as_view(), name='book-comment-detail'),
    path('comments/<uuid:pk>/delete/', BookCommentDeleteView.as_view(), name='book-comment-delete'),
    path('<uuid:pk>/update/', BookUpdateView.as_view(), name='book-update'),
    path('<uuid:pk>/delete/', BookDeleteView.as_view(), name='book-delete'),
    path('my/', MyBooksView.as_view(), name='my-books'),
]
