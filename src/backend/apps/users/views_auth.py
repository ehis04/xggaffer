from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from django.conf import settings
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from .serializers import UserSerializer
from .services.cookie_service import (
    set_auth_cookies,
    clear_auth_cookies,
    get_refresh_token_from_cookie,
)

# handles authentication endpoints that store JWT tokens in secure browser cookies

# Logs a user in, creates JWT tokens, and stores them in authentication cookies
class CookieTokenObtainPairView(APIView):
    permission_classes = [AllowAny]
    # Validates login details, creates access and refresh tokens, and returns the logged-in user
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

# refreshes the access token using the refresh token stored in the browser cookie
class CookieTokenRefreshView(APIView):
    permission_classes = [AllowAny]
    # reads the refresh token from cookies, validates it, and issues a new access token
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

# Logs the user out by blacklisting the refresh token and clearing auth cookies
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    # blacklists the current refresh token, then removes authentication cookies from the response
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

# returns the currently authenticated user's account details
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    # serializes and returns the user attached to the authenticated request
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            'user': serializer.data
        })


# Starts the password reset flow by generating a reset token and emailing it to the user
class RequestPasswordResetView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .models import User
            user = User.objects.get(email=email)
            
            # Generate password reset token
            reset_token = user.generate_password_reset_token()
            
            # Send password reset email
            from .services.email_service import send_password_reset_email
            send_password_reset_email(user, reset_token)
            
            return Response({
                'message': 'If an account exists with this email, you will receive a password reset link.'
            })
        except User.DoesNotExist:
            # Return success message even if user doesn't exist (security best practice)
            return Response({
                'message': 'If an account exists with this email, you will receive a password reset link.'
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to process password reset request: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Completes the password reset flow by validating the token and saving the new password
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    
    # Validates the reset token and password fields before updating the user's password
    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        if not token or not new_password or not confirm_password:
            return Response(
                {'error': 'Token, new password, and confirmation are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_password != confirm_password:
            return Response(
                {'error': 'Passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .models import User
            user = User.objects.get(password_reset_token=token)
            
            # Validate token
            if not user.is_password_reset_token_valid():
                return Response(
                    {'error': 'Password reset link has expired. Please request a new one.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update password
            user.set_password(new_password)
            user.clear_password_reset_token()
            
            return Response({
                'message': 'Password reset successfully. You can now login with your new password.'
            })
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired password reset link'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
            return Response(
                {'error': 'Failed to reset password'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@ensure_csrf_cookie
@require_GET
def csrf_token_view(request):
    return JsonResponse({'csrfToken': get_token(request)})