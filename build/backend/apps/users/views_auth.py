from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.contrib.auth import authenticate
from django.conf import settings

from .serializers import UserSerializer
from .services.cookie_service import (
    set_auth_cookies,
    clear_auth_cookies,
    get_refresh_token_from_cookie,
)

class CookieTokenObtainPairView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        remember_me = request.data.get('remember_me', False)
        
        if not email or not password:
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(request, email=email, password=password)
        
        if user is None:
            return Response(
                {'error': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        serializer = UserSerializer(user)
        response = Response({
            'user': serializer.data,
            'message': 'Login successful'
        })
        
        set_auth_cookies(response, access_token, refresh_token, remember_me)
        
        return response

class CookieTokenRefreshView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        refresh_token = get_refresh_token_from_cookie(request)
        
        if not refresh_token:
            return Response(
                {'error': 'Refresh token not found'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            refresh = RefreshToken(refresh_token)

            access_token = str(refresh.access_token)

            new_refresh_token = refresh_token  
            
            if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS', False):
                if settings.SIMPLE_JWT.get('BLACKLIST_AFTER_ROTATION', False):
                    try:
                        refresh.blacklist()
                    except AttributeError:
                        pass
                
                from .models import User
                user_id = refresh.access_token.payload.get('user_id')
                user = User.objects.get(id=user_id)
                new_refresh = RefreshToken.for_user(user)
                new_refresh_token = str(new_refresh)
                access_token = str(new_refresh.access_token)
            
            response = Response({'message': 'Token refreshed'})
            set_auth_cookies(response, access_token, new_refresh_token, remember_me=True)
            
            return response
            
        except TokenError:
            return Response(
                {'error': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {'error': 'Token refresh failed'},
                status=status.HTTP_401_UNAUTHORIZED
            )

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        refresh_token = get_refresh_token_from_cookie(request)

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass
            except Exception:
                pass
        
        response = Response({'message': 'Logout successful'})
        clear_auth_cookies(response)
        
        return response

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            'user': serializer.data
        })