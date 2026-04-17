from django.urls import path

from . import views

from rest_framework_simplejwt.views import TokenRefreshView

app_name = 'auth_'

urlpatterns = [
    path('user/register/', views.RegisterView.as_view(), name='register'),
    path('user/verify-email/', views.VerifyEmailView.as_view(), name='verify-email'),

    path('token/', views.LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('login-options/', views.LoginChoiceView.as_view(), name='login-options'),

    # QR Authentication endpoints
    path('qr-auth/create/', views.QRAuthCreateView.as_view(), name='qr-auth-create'),
    path('qr-auth/status/', views.QRAuthStatusView.as_view(), name='qr-auth-status'),
    path('qr-auth/confirm/', views.QRAuthConfirmView.as_view(), name='qr-auth-confirm'),
    path('qr-auth/confirmed/', views.QRAuthConfirmedView.as_view(), name='qr-auth-confirmed'),
    path('qr-auth/cancel/', views.QRAuthCancelView.as_view(), name='qr-auth-cancel'),

]
