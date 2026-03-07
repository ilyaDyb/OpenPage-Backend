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

from core.auth_.validators import validate_user_login_data
from core.auth_.serializers import MyTokenObtainPairSerializer, UserCreateSerializer, UserSerializer

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
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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

        try:
            user = validate_user_login_data(username_or_email, password)
        except AuthenticationFailed as e:
            return Response({"detail": str(e)}, status=e.status_code if hasattr(e, 'status_code') else 400)

        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        })



# class LogoutView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     @extend_schema(
#         parameters=[
#             OpenApiParameter(
#                 name="Authorization",
#                 type=str,
#                 location=OpenApiParameter.HEADER,
#                 description="Bearer <access_token> (обязателен для аутентификации)",
#                 required=True,
#                 examples=[
#                     OpenApiExample(
#                         'Пример Bearer токена',
#                         summary='Пример',
#                         value='Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
#                     )
#                 ],
#             )
#         ],
#         request={
#             'application/json': {
#                 'type': 'object',
#                 'properties': {
#                     'refresh': {'type': 'string', 'example': 'refresh_token_string'},
#                 },
#                 'required': ['refresh']
#             }
#         },
#         responses={
#             205: OpenApiTypes.OBJECT,
#             400: OpenApiTypes.OBJECT,
#         }
#     )
#     def post(self, request):
#         refresh_token = request.data.get("refresh")
#         if not refresh_token:
#             return Response({"detail": "Refresh token is required"}, status=400)

#         try:
#             token = RefreshToken(refresh_token)
#             if str(token.payload.get('user_id')) != str(request.user.id):
#                 return Response({"detail": "Token does not belong to you"}, status=400)

#             token.blacklist()
#             return Response({"detail": "You have successfully logged out"}, status=205)
#         except Exception as e:
#             return Response({"detail": str(e)}, status=400)