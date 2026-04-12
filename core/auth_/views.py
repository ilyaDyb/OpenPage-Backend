from django.shortcuts import render
from django.contrib.auth import get_user_model, authenticate
from django.conf import settings

import logging

logger = logging.getLogger(__name__)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import generics, status, permissions

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from core.auth_.serializers import MyTokenObtainPairSerializer, UserCreateSerializer, UserSerializer, EmailVerifySerializer, QRSessionRequestSerializer, QRLoginConfirmSerializer, TelegramLinkSerializer, LoginChoiceSerializer, QRAuthRequestSerializer, QRAuthStatusSerializer, QRAuthConfirmSerializer, QRAuthConfirmedSerializer
from core.auth_.utils import generate_verification_code, send_verification_email, store_registration_data, get_registration_data, delete_registration_data
from core.auth_.models import QRAuthRequest

User = get_user_model()

logger = logging.getLogger(__name__)

class MyTokenObtaionPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=UserCreateSerializer,
        responses={201: UserCreateSerializer, 400: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data['email']

        if get_registration_data(email):
            return Response(
                {"detail": "Registration already in progress. Check your email for the code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        code = generate_verification_code()
        user_data = {
            'username': data['username'],
            'email': email,
            'password': data['password'],
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
        }
        store_registration_data(email, user_data, code)

        send_verification_email(email, code)

        return Response(
            {"detail": "Verification code sent to email."},
            status=status.HTTP_200_OK
        )


class LoginView(APIView):
    authentication_classes = []

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'username_or_email': {'type': 'string', 'example': 'user@example.com'},
                    'password': {'type': 'string', 'example': 'mypassword'},
                },
                'required': ['username_or_email', 'password']
            }
        },
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT
        }
    )
    def post(self, request):
            username_or_email = request.data.get("username_or_email")
            password = request.data.get("password")

            user = authenticate(username=username_or_email, password=password)
            if not user:
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass

            if not user:
                raise AuthenticationFailed("Invalid credentials")


            if not user.email_confirmed:
                return Response(
                    {"detail": "Email not confirmed."},
                    status=status.HTTP_403_FORBIDDEN
                )

            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            })

class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=EmailVerifySerializer,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        data = get_registration_data(email)
        if not data:
            return Response(
                {"detail": "Registration data not found or expired."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if data.get('code') != code:
            return Response(
                {"detail": "Invalid code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            email_confirmed=True
        )

        delete_registration_data(email)

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class LoginChoiceView(APIView):
    """
    Returns available login options when user is unauthorized.
    Suggests email or Telegram QR code login.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        responses={
            200: LoginChoiceSerializer
        }
    )
    def get(self, request):
        return Response({
            "message": "Please choose a login method",
            "options": [
                {
                    "type": "email",
                    "label": "Login with Email",
                    "endpoint": "/api/token/",
                    "description": "Use your email and password"
                },
                {
                    "type": "telegram_qr",
                    "label": "Login with Telegram QR Code",
                    "endpoint": "/api/qr-session/create/",
                    "description": "Scan QR code via Telegram bot",
                    "requirements": ["Linked Telegram account"]
                }
            ]
        })


class QRAuthCreateView(APIView):
    """
    Create a new QR authentication request.
    Returns a token and QR link for the frontend.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    serializer_class = QRAuthRequestSerializer

    @extend_schema(
        summary="Create QR Authentication Request",
        description="Creates a new QR code authentication session. Frontend should display the QR code from qr_link.",
        tags=['QR Authentication'],
        responses={
            200: QRAuthRequestSerializer,
            500: OpenApiTypes.OBJECT
        }
    )
    def post(self, request):
        from datetime import timedelta
        from django.utils import timezone
        
        logger.info(f"📥 POST /api/qr-auth/create/ - Creating new QR auth request")
        logger.debug(f"Request headers: {dict(request.headers)}")
        logger.debug(f"Request data: {request.data}")
        
        try:
            # Create new QR auth request
            expires_at = timezone.now() + timedelta(minutes=5)
            qr_request = QRAuthRequest.objects.create(expires_at=expires_at)
            
            logger.info(f"✅ Created QR auth request: token={qr_request.token}, expires_at={expires_at}")
            
            # Generate Telegram bot link
            bot_username = "OpenPageAuthBot"
            qr_link = f"https://t.me/{bot_username}?start=qrlogin_{qr_request.token}"
            
            logger.info(f"🔗 Generated QR link: {qr_link}")
            
            # Generate QR code image
            qr_code_relative_url = qr_request.generate_qr_code_image(qr_link)
            qr_code_full_url = request.build_absolute_uri(f"/media/{qr_code_relative_url}")
            
            logger.info(f"🖼️ Generated QR code image: {qr_code_full_url}")
            
            return Response({
                'token': str(qr_request.token),
                'qr_link': qr_link,
                'qr_code_url': qr_code_full_url,
                'expires_in': 300  # 5 minutes in seconds
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"❌ Failed to create QR auth request: {type(e).__name__}: {e}", exc_info=True)
            return Response(
                {'detail': 'Failed to create QR auth request'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QRAuthStatusView(APIView):
    """
    Check the status of a QR authentication request.
    Frontend polls this endpoint until authentication is complete.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Check QR Authentication Status",
        description="Poll this endpoint to check if user has scanned and confirmed the QR code. Returns JWT tokens when authenticated.",
        tags=['QR Authentication'],
        parameters=[
            OpenApiParameter(
                name='token',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='QR authentication token from qr-auth/create/',
                required=True
            )
        ],
        responses={
            200: QRAuthStatusSerializer,
            404: OpenApiTypes.OBJECT
        }
    )
    def get(self, request):
        token = request.query_params.get('token')
        
        logger.info(f"📥 GET /api/qr-auth/status/ - Checking status for token: {token}")
        
        if not token:
            logger.warning("⚠️ Token parameter missing in status request")
            return Response(
                {"detail": "Token required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            qr_request = QRAuthRequest.objects.get(token=token)
            logger.debug(f"✅ Found QR request: {qr_request.token}, status={qr_request.status}")
        except QRAuthRequest.DoesNotExist:
            logger.warning(f"⚠️ QR request not found for token: {token}")
            return Response(
                {"detail": "Invalid token"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if expired
        if qr_request.is_expired() and qr_request.status != 'confirmed':
            logger.info(f"⏰ QR request expired: {token}")
            qr_request.status = 'expired'
            qr_request.save()
            return Response({
                'status': 'expired',
                'authenticated': False,
                'message': 'QR code has expired. Please refresh and try again.'
            })
        
        # If confirmed, generate tokens
        if qr_request.status == 'confirmed' and qr_request.user:
            user = qr_request.user
            logger.info(f"✅ QR request confirmed, generating tokens for user: {user.username}")
            
            # Update user's telegram info if not set
            if not user.telegram_id and qr_request.telegram_id:
                user.telegram_id = qr_request.telegram_id
                user.telegram_confirmed = True
                user.save()
                logger.info(f"🔗 Linked Telegram ID {qr_request.telegram_id} to user {user.username}")
            
            refresh = RefreshToken.for_user(user)
            logger.info(f"🎫 Generated JWT tokens for user {user.username}")
            
            return Response({
                'status': 'confirmed',
                'authenticated': True,
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': UserSerializer(user).data
            })
        
        # Still pending or scanned
        logger.debug(f"⏳ QR request still pending/scanned: {token}, status={qr_request.status}")
        return Response({
            'status': qr_request.status,
            'authenticated': False,
            'message': 'Waiting for QR code scan...'
        })


class QRAuthConfirmView(APIView):
    """
    Endpoint for Telegram bot to confirm QR scan.
    Called when user scans QR code and sends /start command.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=QRAuthConfirmSerializer,
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = QRAuthConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        telegram_id = serializer.validated_data['telegram_id']
        telegram_username = serializer.validated_data.get('telegram_username', '')
        
        logger.info(f"📥 POST /api/qr-auth/confirm/ - token={token}, telegram_id={telegram_id}, username={telegram_username}")
        logger.debug(f"Request data: {request.data}")
        
        try:
            qr_request = QRAuthRequest.objects.get(token=token)
            logger.debug(f"✅ Found QR request: {qr_request.token}, status={qr_request.status}")
        except QRAuthRequest.DoesNotExist:
            logger.warning(f"⚠️ QR request not found for token: {token}")
            return Response(
                {'success': False, 'error': 'Invalid or expired token'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if expired
        if qr_request.is_expired():
            logger.warning(f"⏰ Token expired: {token}")
            return Response(
                {'success': False, 'error': 'Token has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already confirmed
        if qr_request.status in ['confirmed', 'cancelled', 'expired']:
            logger.warning(f"⚠️ Token already in state {qr_request.status}: {token}")
            return Response(
                {'success': False, 'error': f'Token already {qr_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update with Telegram info
        qr_request.telegram_id = telegram_id
        qr_request.telegram_username = telegram_username
        qr_request.status = 'scanned'
        qr_request.save()
        logger.info(f"✅ Updated QR request: {token} -> status=scanned, telegram_id={telegram_id}")
        
        # Get or create user
        try:
            user = User.objects.get(telegram_id=telegram_id)
            logger.info(f"👤 Found existing user with telegram_id {telegram_id}: {user.username}")
        except User.DoesNotExist:
            # Create new user with telegram info
            username = telegram_username or f"tg_user_{telegram_id}"
            # Make username unique if needed
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=f"{username}@telegram.local",
                password=None,  # No password for Telegram-only users
                telegram_id=telegram_id,
                telegram_confirmed=True
            )
            logger.info(f"🆕 Created new user: {user.username} (telegram_id={telegram_id})")
        
        # Link user to QR request
        qr_request.user = user
        qr_request.save()
        logger.info(f"🔗 Linked user {user.username} to QR request {token}")
        
        return Response({
            'success': True,
            'username': user.username,
            'expires_in': 300
        })


class QRAuthConfirmedView(APIView):
    """
    Final confirmation endpoint.
    Called when user clicks "Confirm Login" button in Telegram bot.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=QRAuthConfirmedSerializer,
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = QRAuthConfirmedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        telegram_id = serializer.validated_data['telegram_id']
        
        logger.info(f"📥 POST /api/qr-auth/confirmed/ - token={token}, telegram_id={telegram_id}")
        
        try:
            qr_request = QRAuthRequest.objects.get(
                token=token,
                telegram_id=telegram_id
            )
            logger.debug(f"✅ Found QR request: {qr_request.token}, status={qr_request.status}")
        except QRAuthRequest.DoesNotExist:
            logger.warning(f"⚠️ QR request not found for token={token}, telegram_id={telegram_id}")
            return Response(
                {'success': False, 'error': 'Invalid token'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify not expired
        if qr_request.is_expired():
            logger.warning(f"⏰ Token expired: {token}")
            return Response(
                {'success': False, 'error': 'Token has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mark as confirmed
        from django.utils import timezone
        qr_request.status = 'confirmed'
        qr_request.confirmed_at = timezone.now()
        qr_request.save()
        logger.info(f"✅ QR request confirmed: {token} at {qr_request.confirmed_at}")
        
        return Response({'success': True})


class QRAuthCancelView(APIView):
    """
    Cancel QR authentication.
    Can be called by frontend or Telegram bot.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        token = request.data.get('token')
        
        logger.info(f"📥 POST /api/qr-auth/cancel/ - token={token}")
        
        if not token:
            logger.warning("⚠️ Cancel request missing token")
            return Response(
                {'success': False, 'error': 'Token required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            qr_request = QRAuthRequest.objects.get(token=token)
            logger.debug(f"✅ Found QR request: {qr_request.token}, status={qr_request.status}")
        except QRAuthRequest.DoesNotExist:
            logger.warning(f"⚠️ QR request not found for token: {token}")
            return Response(
                {'success': False, 'error': 'Invalid token'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Only cancel if still pending or scanned
        if qr_request.status in ['pending', 'scanned']:
            qr_request.status = 'cancelled'
            qr_request.save()
            logger.info(f"🚫 QR request cancelled: {token}")
        else:
            logger.info(f"ℹ️ Cannot cancel QR request in state {qr_request.status}: {token}")
        
        return Response({'success': True})
