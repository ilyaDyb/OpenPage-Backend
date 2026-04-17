import logging
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core.api_errors import error_response
from core.auth_.models import QRAuthRequest
from core.auth_.permissions import HasAPISecretKey
from core.auth_.serializers import (
    DetailResponseSerializer,
    EmailVerifySerializer,
    LoginChoiceSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    MyTokenObtainPairSerializer,
    QRAuthActionResponseSerializer,
    QRAuthCancelSerializer,
    QRAuthConfirmSerializer,
    QRAuthConfirmedSerializer,
    QRAuthRequestSerializer,
    QRAuthStatusSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from core.auth_.utils import (
    delete_registration_data,
    generate_verification_code,
    get_registration_data,
    send_verification_email,
    store_registration_data,
)


logger = logging.getLogger(__name__)
User = get_user_model()


class MyTokenObtaionPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id='auth_register',
        summary='Register user',
        description='Start registration flow and send verification code to email.',
        tags=['Authentication'],
        request=UserCreateSerializer,
        responses={200: DetailResponseSerializer, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data['email']

        if get_registration_data(email):
            logger.warning("Registration already in progress for %s", email)
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'email': ['Registration already in progress. Check your email for the code.']},
            )

        code = generate_verification_code()
        user_data = {
            'username': data['username'],
            'email': email,
            'password': data['password'],
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
        }

        try:
            send_verification_email(email, code)
        except Exception:
            logger.exception("Failed to send verification email to %s", email)
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'email': ['Failed to send verification code to this email.']},
            )

        store_registration_data(email, user_data, code)
        logger.info("Verification code sent to %s", email)
        return Response({'detail': 'Verification code sent to email.'}, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id='auth_login',
        summary='Login',
        description='Authenticate by username or email and return JWT tokens.',
        tags=['Authentication'],
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: DetailResponseSerializer,
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username_or_email = serializer.validated_data['username_or_email']
        password = serializer.validated_data['password']

        user = authenticate(username=username_or_email, password=password)
        if not user:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if not user:
            logger.warning("Failed login attempt for %s", username_or_email)
            raise AuthenticationFailed('Invalid credentials')

        if not user.email_confirmed:
            logger.warning("Blocked login for unconfirmed email user %s", user.username)
            return error_response(
                error_type='permission_denied',
                detail='Email not confirmed.',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        logger.info("User %s logged in", user.username)
        return Response(
            {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data,
            }
        )


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id='auth_verify_email',
        summary='Verify email',
        description='Confirm registration email code and create the user account.',
        tags=['Authentication'],
        request=EmailVerifySerializer,
        responses={201: LoginResponseSerializer, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        data = get_registration_data(email)
        if not data:
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'email': ['Registration data not found or expired.']},
            )

        if data.get('code') != code:
            logger.warning("Invalid verification code for %s", email)
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'code': ['Invalid code.']},
            )

        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            email_confirmed=True,
        )

        delete_registration_data(email)
        refresh = RefreshToken.for_user(user)
        logger.info("User %s completed email verification", user.username)
        return Response(
            {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginChoiceView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id='auth_login_choices',
        summary='Login options',
        description='Return available authentication methods for the client.',
        tags=['Authentication'],
        responses={200: LoginChoiceSerializer},
    )
    def get(self, request):
        return Response(
            {
                'message': 'Please choose a login method',
                'options': [
                    {
                        'type': 'email',
                        'label': 'Login with Email',
                        'endpoint': '/api/token/',
                        'description': 'Use your email and password',
                    },
                    {
                        'type': 'telegram_qr',
                        'label': 'Login with Telegram QR Code',
                        'endpoint': '/api/qr-auth/create/',
                        'description': 'Scan QR code via Telegram bot',
                        'requirements': ['Linked Telegram account'],
                    },
                ],
            }
        )


class QRAuthCreateView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    serializer_class = QRAuthRequestSerializer

    @extend_schema(
        operation_id='auth_qr_create',
        summary='Create QR auth request',
        description='Create a QR authentication session for the frontend.',
        tags=['QR Authentication'],
        responses={200: QRAuthRequestSerializer, 500: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        logger.info("Creating QR auth request")

        try:
            expires_at = timezone.now() + timedelta(minutes=5)
            qr_request = QRAuthRequest.objects.create(expires_at=expires_at)
            bot_username = "OpenPageAuthBot"
            qr_link = f"https://t.me/{bot_username}?start=qrlogin_{qr_request.token}"
            qr_code_relative_url = qr_request.generate_qr_code_image(qr_link)
            qr_code_full_url = request.build_absolute_uri(f"/media/{qr_code_relative_url}")

            logger.info("QR auth request %s created", qr_request.token)
            return Response(
                {
                    'token': str(qr_request.token),
                    'qr_link': qr_link,
                    'qr_code_url': qr_code_full_url,
                    'expires_in': 300,
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            logger.exception("Failed to create QR auth request")
            return error_response(
                error_type='server_error',
                detail='Failed to create QR auth request',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class QRAuthStatusView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id='auth_qr_status',
        summary='Check QR auth status',
        description='Poll QR auth request status and return tokens after confirmation.',
        tags=['QR Authentication'],
        parameters=[
            OpenApiParameter(
                name='token',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='QR authentication token from /api/qr-auth/create/.',
                required=True,
            )
        ],
        responses={200: QRAuthStatusSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        token = request.query_params.get('token')
        if not token:
            logger.warning("QR auth status requested without token")
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'token': ['This query parameter is required.']},
            )

        try:
            qr_request = QRAuthRequest.objects.get(token=token)
        except QRAuthRequest.DoesNotExist:
            logger.warning("QR auth request not found for token %s", token)
            return error_response(
                error_type='not_found',
                detail='Invalid token',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if qr_request.is_expired() and qr_request.status != 'confirmed':
            qr_request.status = 'expired'
            qr_request.save(update_fields=['status'])
            logger.info("QR auth request %s expired", token)
            return Response(
                {
                    'status': 'expired',
                    'authenticated': False,
                    'message': 'QR code has expired. Please refresh and try again.',
                }
            )

        if qr_request.status == 'confirmed' and qr_request.user:
            user = qr_request.user
            if not user.telegram_id and qr_request.telegram_id:
                user.telegram_id = qr_request.telegram_id
                user.telegram_confirmed = True
                user.save(update_fields=['telegram_id', 'telegram_confirmed'])

            refresh = RefreshToken.for_user(user)
            logger.info("QR auth request %s confirmed for user %s", token, user.username)
            return Response(
                {
                    'status': 'confirmed',
                    'authenticated': True,
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh),
                    'user': UserSerializer(user).data,
                }
            )

        return Response(
            {
                'status': qr_request.status,
                'authenticated': False,
                'message': 'Waiting for QR code scan...',
            }
        )


class QRAuthConfirmView(APIView):
    permission_classes = [HasAPISecretKey]
    authentication_classes = []

    @extend_schema(
        operation_id='auth_qr_confirm',
        summary='Confirm QR scan',
        description='Internal bot endpoint: bind Telegram scan result to QR auth request.',
        tags=['QR Authentication'],
        request=QRAuthConfirmSerializer,
        responses={200: QRAuthActionResponseSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = QRAuthConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        telegram_id = serializer.validated_data['telegram_id']
        telegram_username = serializer.validated_data.get('telegram_username', '')

        try:
            qr_request = QRAuthRequest.objects.get(token=token)
        except QRAuthRequest.DoesNotExist:
            logger.warning("QR confirm failed: request %s not found", token)
            return error_response(
                error_type='not_found',
                detail='Invalid or expired token',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if qr_request.is_expired():
            logger.warning("QR confirm rejected for expired token %s", token)
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'token': ['Token has expired']},
            )

        if qr_request.status in {'confirmed', 'cancelled', 'expired'}:
            logger.warning("QR confirm rejected for token %s in status %s", token, qr_request.status)
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'token': [f'Token already {qr_request.status}']},
            )

        qr_request.telegram_id = telegram_id
        qr_request.telegram_username = telegram_username
        qr_request.status = 'scanned'
        qr_request.save(update_fields=['telegram_id', 'telegram_username', 'status'])

        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            username = telegram_username or f"tg_user_{telegram_id}"
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=f"{username}@telegram.local",
                password=None,
                telegram_id=telegram_id,
                telegram_confirmed=True,
                email_confirmed=True,
            )
            logger.info("Created Telegram-only user %s", user.username)

        qr_request.user = user
        qr_request.save(update_fields=['user'])
        logger.info("QR scan confirmed for user %s and token %s", user.username, token)
        return Response({'success': True, 'username': user.username, 'expires_in': 300})


class QRAuthConfirmedView(APIView):
    permission_classes = [HasAPISecretKey]
    authentication_classes = []

    @extend_schema(
        operation_id='auth_qr_confirmed',
        summary='Finalize QR auth',
        description='Internal bot endpoint: mark QR auth session as confirmed.',
        tags=['QR Authentication'],
        request=QRAuthConfirmedSerializer,
        responses={200: QRAuthActionResponseSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = QRAuthConfirmedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        telegram_id = serializer.validated_data['telegram_id']

        try:
            qr_request = QRAuthRequest.objects.get(token=token, telegram_id=telegram_id)
        except QRAuthRequest.DoesNotExist:
            logger.warning("QR final confirm failed for token %s and telegram_id %s", token, telegram_id)
            return error_response(
                error_type='not_found',
                detail='Invalid token',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if qr_request.is_expired():
            logger.warning("QR final confirm rejected for expired token %s", token)
            return error_response(
                error_type='validation_error',
                detail='Validation failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={'token': ['Token has expired']},
            )

        qr_request.status = 'confirmed'
        qr_request.confirmed_at = timezone.now()
        qr_request.save(update_fields=['status', 'confirmed_at'])
        logger.info("QR auth request %s marked as confirmed", token)
        return Response({'success': True})


class QRAuthCancelView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id='auth_qr_cancel',
        summary='Cancel QR auth',
        description='Cancel an active QR authentication request.',
        tags=['QR Authentication'],
        request=QRAuthCancelSerializer,
        responses={200: QRAuthActionResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = QRAuthCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        try:
            qr_request = QRAuthRequest.objects.get(token=token)
        except QRAuthRequest.DoesNotExist:
            logger.warning("QR cancel failed for missing token %s", token)
            return error_response(
                error_type='not_found',
                detail='Invalid token',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if qr_request.status in {'pending', 'scanned'}:
            qr_request.status = 'cancelled'
            qr_request.save(update_fields=['status'])
            logger.info("QR auth request %s cancelled", token)

        return Response({'success': True})
