"""
Views для профилей пользователей
"""
import logging
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, RetrieveUpdateAPIView, get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiTypes, OpenApiParameter
from django.contrib.auth import get_user_model
from core.profiles.models import ReaderProfile, AuthorProfile
from core.profiles.serializers import UserProfileSerializer, UserSerializer, ReaderProfileSerializer, AuthorProfileSerializer

logger = logging.getLogger(__name__)


class CurrentUserProfileView(RetrieveUpdateAPIView):
    """
    Получение и обновление профиля текущего пользователя
    
    GET /api/profile/ - получить данные профиля
    PUT /api/profile/ - обновить данные профиля
    PATCH /api/profile/ - частично обновить данные профиля
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Профиль текущего пользователя",
        description="Возвращает данные профиля авторизованного пользователя, включая reader_profile и author_profile (если существует)",
        tags=['User Profiles'],
        parameters=[
            OpenApiParameter(
                name='Authorization',
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description='Bearer токен доступа',
                default='Bearer <TOKEN>'
            ),
        ],
        responses={
            200: UserProfileSerializer,
            401: OpenApiTypes.OBJECT
        }
    )
    def get(self, request, *args, **kwargs):
        logger.info(f"📥 GET /api/profile/ - Пользователь: {request.user.username}")
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Обновление профиля",
        description="Обновляет email, first_name, last_name текущего пользователя",
        tags=['User Profiles'],
        request=UserProfileSerializer,
        parameters=[
            OpenApiParameter(
                name='Authorization',
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description='Bearer токен доступа',
                default='Bearer <TOKEN>'
            ),
        ],
        responses={
            200: UserProfileSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT
        }
    )
    def put(self, request, *args, **kwargs):
        logger.info(f"📝 PUT /api/profile/ - Обновление профиля пользователя: {request.user.username}")
        return super().put(request, *args, **kwargs)
    
    @extend_schema(
        summary="Частичное обновление профиля",
        description="Частично обновляет данные профиля (PATCH)",
        tags=['User Profiles'],
        request=UserProfileSerializer,
        parameters=[
            OpenApiParameter(
                name='Authorization',
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description='Bearer токен доступа',
                default='Bearer <TOKEN>'
            ),
        ],
        responses={
            200: UserProfileSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT
        }
    )
    def patch(self, request, *args, **kwargs):
        logger.info(f"🔧 PATCH /api/profile/ - Частичное обновление профиля: {request.user.username}")
        return super().patch(request, *args, **kwargs)
    
    def get_object(self):
        """Возвращает текущего пользователя"""
        return self.request.user
    
    def perform_update(self, serializer):
        """Сохраняет обновленные данные"""
        serializer.save()
        logger.info(f"✅ Профиль пользователя {self.request.user.username} успешно обновлен")


class PublicUserProfileView(RetrieveAPIView):
    """
    Просмотр профиля другого пользователя (публичный доступ)
    
    GET /api/profile/<int:pk>/ - получить профиль по ID
    GET /api/profile/<str:username>/ - получить профиль по username
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        summary="Публичный профиль пользователя",
        description="Возвращает данные профиля пользователя по ID (без чувствительной информации)",
        tags=['User Profiles'],
        parameters=[],
        responses={
            200: UserProfileSerializer,
            404: OpenApiTypes.OBJECT
        }
    )
    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        logger.info(f"📥 GET /api/profile/{pk}/ - Публичный профиль")
        return super().get(request, *args, **kwargs)
    
    def get_object(self):
        """Получает пользователя по pk из URL"""
        pk = self.kwargs.get('pk')
        queryset = User.objects.select_related('reader_profile', 'author_profile').all()
        obj = get_object_or_404(queryset, pk=pk)
        self.check_object_permissions(self.request, obj)
        return obj


class UserByUsernameProfileView(RetrieveAPIView):
    """
    Просмотр профиля пользователя по username
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        summary="Профиль пользователя по username",
        description="Возвращает данные профиля пользователя по username",
        tags=['User Profiles'],
        responses={
            200: UserProfileSerializer,
            404: OpenApiTypes.OBJECT
        }
    )
    def get(self, request, *args, **kwargs):
        username = kwargs.get('username')
        logger.info(f"📥 GET /api/profile/username/{username}/")
        return super().get(request, *args, **kwargs)
    
    def get_object(self):
        """Получает пользователя по username"""
        username = self.kwargs.get('username')
        queryset = User.objects.select_related('reader_profile', 'author_profile').all()
        obj = get_object_or_404(queryset, username=username)
        self.check_object_permissions(self.request, obj)
        return obj


class CreateReaderProfileView(APIView):
    """
    Создание профиля читателя для текущего пользователя
    Используется при регистрации или первом входе
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Создать профиль читателя",
        description="Создает профиль читателя для текущего пользователя (если еще не существует)",
        tags=['User Profiles'],
        parameters=[
            OpenApiParameter(
                name='Authorization',
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description='Bearer токен доступа',
                default='Bearer <TOKEN>'
            ),
        ],
        responses={
            201: ReaderProfileSerializer,
            400: OpenApiTypes.OBJECT
        }
    )
    def post(self, request):
        logger.info(f"📝 POST /api/profile/create-reader/ - Создание профиля читателя")
        
        if hasattr(request.user, 'reader_profile'):
            return Response(
                {'error': 'Профиль читателя уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reader_profile = ReaderProfile.objects.create(user=request.user)
        
        logger.info(f"✅ Создан профиль читателя для пользователя {request.user.username}")
        
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CreateAuthorProfileView(APIView):
    """
    Создание профиля автора для текущего пользователя
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Создать профиль автора",
        description="Создает профиль автора для текущего пользователя (отправляет запрос на модерацию)",
        tags=['User Profiles'],
        request=AuthorProfileSerializer,
        parameters=[
            OpenApiParameter(
                name='Authorization',
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description='Bearer токен доступа',
                default='Bearer <TOKEN>'
            ),
        ],
        responses={
            201: AuthorProfileSerializer,
            400: OpenApiTypes.OBJECT
        }
    )
    def post(self, request):
        logger.info(f"📝 POST /api/profile/create-author/ - Создание профиля автора")
        
        if hasattr(request.user, 'author_profile'):
            return Response(
                {'error': 'Профиль автора уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )
        

        serializer = AuthorProfileSerializer(data=request.data)
        
        if serializer.is_valid():
            author_profile = serializer.save(user=request.user, requested_at=timezone.now())
            
            logger.info(f"✅ Создан профиль автора для пользователя {request.user.username}")
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        logger.error(f"❌ Ошибка валидации: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)