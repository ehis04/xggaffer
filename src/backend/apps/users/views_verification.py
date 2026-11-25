from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import User
from .services.email_service import send_verification_email

# Handles email verification endpoints for sending verification emails, resending them, verifying tokens, and checking verification status

# Sends a verification email to the currently authenticated user
class SendVerificationEmailView(APIView):
    permission_classes = [IsAuthenticated]
    
    # Sends a verification link unless the user's email is already verified
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

# Resends a verification email to the currently authenticated user
class ResendVerificationEmailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # Sends another verification link unless the user's email is already verified
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

# Verifies a user's email address using a verification token submitted from the frontend
class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    # Validates the token, checks expiry, and marks the matching user email as verified
    def post(self, request):
        token = request.data.get('token')

        if not token:
            return Response(
                {'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(verification_token=token)
        except User.DoesNotExist:
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

# Returns the email verification state for the currently authenticated user
class VerificationStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'email_verified': request.user.email_verified,
            'email': request.user.email
        })
