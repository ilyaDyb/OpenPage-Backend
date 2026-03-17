from django.shortcuts import render
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import generics, status, permissions

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from core.auth_.serializers import MyTokenObtainPairSerializer, UserCreateSerializer, UserSerializer, EmailVerifySerializer
from core.auth_.utils import generate_verification_code, send_verification_email, store_registration_data, get_registration_data, delete_registration_data

User = get_user_model()

class CustomJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        jti = token['jti']
        if BlacklistedToken.objects.filter(token__jti=jti).exists():
            raise InvalidToken({"detail": "Token is blacklisted"})
        return token
    

class MyTokenObtaionPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]

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
