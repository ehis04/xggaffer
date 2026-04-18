from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import User
from .services.email_service import send_verification_email


class SendVerificationEmailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.email_verified:
            return Response(
                {'message': 'Email is already verified'},
                status=status.HTTP_200_OK
            )
        
        success = send_verification_email(user)
        
        if success:
            return Response(
                {'message': 'Verification email sent'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Failed to send verification email'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResendVerificationEmailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.email_verified:
            return Response(
                {'message': 'Email is already verified'},
                status=status.HTTP_200_OK
            )
        
        success = send_verification_email(user)
        
        if success:
            return Response(
                {'message': 'Verification email resent'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Failed to resend verification email'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        print(f"DEBUG: Received token: {token}")

        if not token:
            print("DEBUG: No token provided")
            return Response(
                {'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(verification_token=token)
            print(f"DEBUG: Found user: {user.email}")
        except User.DoesNotExist:
            print(f"DEBUG: No user found with token: {token}")
            # Check if any user has a similar token
            all_users_with_tokens = User.objects.filter(verification_token__isnull=False).values_list('email', 'verification_token')
            print(f"DEBUG: Users with tokens: {list(all_users_with_tokens)}")
            return Response(
                {'error': 'Invalid or expired verification link. Please request a new verification email.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if already verified
        if user.email_verified:
            return Response(
                {
                    'message': 'Email already verified',
                    'already_verified': True
                },
                status=status.HTTP_200_OK
            )

        if not user.is_token_valid():
            return Response(
                {'error': 'Verification token has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.verify_email()

        return Response(
            {
                'message': 'Email verified successfully',
                'already_verified': False
            },
            status=status.HTTP_200_OK
        )


class VerificationStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'email_verified': request.user.email_verified,
            'email': request.user.email
        })