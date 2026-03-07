from django.urls import path

from . import views

from rest_framework_simplejwt.views import TokenRefreshView

app_name = 'auth_'

urlpatterns = [
    path('user/register/', views.RegisterView.as_view(), name='register'),

    path('token/', views.LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='logout'),

]
