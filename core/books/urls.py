# """
# URL-маршруты для книг и жанров
# """
# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from core.books.views import (
#     GenreListView,
#     GenreDetailView,
#     BookListView,
#     BookDetailView,
#     BookBySlugView,
#     BookCreateView,
#     BookUpdateView,
#     BookDeleteView,
#     MyBooksView,
# )

# app_name = 'books'

# urlpatterns = [
#     # Жанры
#     path('genres/', GenreListView.as_view(), name='genre-list'),
#     path('genres/<uuid:pk>/', GenreDetailView.as_view(), name='genre-detail'),
    
#     # Книги
#     path('', BookListView.as_view(), name='book-list'),
#     path('<uuid:pk>/', BookDetailView.as_view(), name='book-detail'),
#     path('slug/<str:slug>/', BookBySlugView.as_view(), name='book-by-slug'),
#     path('create/', BookCreateView.as_view(), name='book-create'),
#     path('<uuid:pk>/update/', BookUpdateView.as_view(), name='book-update'),
#     path('<uuid:pk>/delete/', BookDeleteView.as_view(), name='book-delete'),
#     path('my/', MyBooksView.as_view(), name='my-books'),
# ]
