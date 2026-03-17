from django.urls import path

from . import views

from rest_framework_simplejwt.views import TokenRefreshView

app_name = 'auth_'

urlpatterns = [
    path('user/register/', views.RegisterView.as_view(), name='register'),
    path('user/verify-email/', views.VerifyEmailView.as_view(), name='verify-email'),

    path('token/', views.LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='logout'),

]
