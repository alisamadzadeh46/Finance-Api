from django.contrib.auth import authenticate
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from users import serializers as s
from users import models as m


# ── helpers ───────────────────────────────────────────────────────────────────

def _set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        key="refresh",
        value=str(refresh_token),
        httponly=True,
        max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
        samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
        secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', not settings.DEBUG),
    )


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    @extend_schema(
        tags=['Auth'],
        summary='Register a new user',
        request=s.UserRegisterSerializer,
        responses={
            201: OpenApiResponse(description='User registered. Returns access token.'),
            400: OpenApiResponse(description='Validation error'),
        }
    )
    def post(self, request):
        serializer = s.UserRegisterSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            response = Response(
                {'access': str(refresh.access_token), 'message': 'Registered successfully.'},
                status=status.HTTP_201_CREATED
            )
            _set_refresh_cookie(response, refresh)
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    @extend_schema(
        tags=['Auth'],
        summary='Login with email and password',
        request=s.UserRegisterSerializer,
        responses={
            200: OpenApiResponse(description='Login successful. Returns access token.'),
            400: OpenApiResponse(description='Missing credentials'),
            401: OpenApiResponse(description='Invalid credentials'),
        }
    )
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        if not email or not password:
            return Response({"error": "Please provide both email and password."},
                            status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(username=email, password=password)
        if not user:
            return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        response = Response({'access': str(refresh.access_token)}, status=status.HTTP_200_OK)
        _set_refresh_cookie(response, refresh)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Auth'],
        summary='Logout — blacklists the refresh token',
        responses={
            200: OpenApiResponse(description='Logged out successfully.'),
            400: OpenApiResponse(description='No refresh token found or token invalid.'),
        }
    )
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token not found."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            response = Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)
            response.delete_cookie("refresh")
            return response
        except (TokenError, InvalidToken):
            return Response({"error": "Invalid or expired refresh token."},
                            status=status.HTTP_400_BAD_REQUEST)


class TokenRefreshView(APIView):
    @extend_schema(
        tags=['Auth'],
        summary='Refresh access token using httpOnly cookie',
        responses={
            200: OpenApiResponse(description='Returns new access token.'),
            401: OpenApiResponse(description='No valid refresh token in cookie.'),
        }
    )
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh")
        if not refresh_token:
            return Response({"error": "No refresh token found in cookie."},
                            status=status.HTTP_401_UNAUTHORIZED)
        try:
            token = RefreshToken(refresh_token)
            new_access = str(token.access_token)
            response = Response({"access": new_access}, status=status.HTTP_200_OK)
            if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
                token.blacklist()
                new_refresh = RefreshToken.for_user(
                    m.User.objects.get(id=token["user_id"])
                )
                _set_refresh_cookie(response, new_refresh)
            return response
        except (TokenError, InvalidToken):
            return Response({"error": "Invalid or expired refresh token."},
                            status=status.HTTP_401_UNAUTHORIZED)


# ── Profile ───────────────────────────────────────────────────────────────────

class UserView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Profile'],
        summary='Get current user profile',
        responses={200: s.UserSerializer}
    )
    def get(self, request):
        serializer = s.UserSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        tags=['Profile'],
        summary='Update current user profile',
        request=s.UserUpdateSerializer,
        responses={200: s.UserSerializer}
    )
    def patch(self, request):
        serializer = s.UserUpdateSerializer(request.user, data=request.data,
                                            partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(s.UserSerializer(request.user).data)


# ── KYC ───────────────────────────────────────────────────────────────────────

class KYCSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['KYC'],
        summary='Get current KYC status',
        responses={200: s.KYCSerializer, 404: OpenApiResponse(description='KYC not submitted yet.')}
    )
    def get(self, request):
        try:
            kyc = request.user.kyc_profile
            return Response(s.KYCSerializer(kyc).data)
        except m.KYC.DoesNotExist:
            return Response({"detail": "KYC not submitted yet."}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        tags=['KYC'],
        summary='Submit KYC for identity verification',
        request=s.KYCCreateSerializer,
        responses={
            201: s.KYCSerializer,
            400: OpenApiResponse(description='Validation error or already submitted.'),
        }
    )
    def post(self, request):
        serializer = s.KYCCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        kyc = serializer.save()
        kyc.verification_status = m.KYC.VerificationStatus.PENDING
        kyc.save(update_fields=['verification_status'])
        return Response(s.KYCSerializer(kyc).data, status=status.HTTP_201_CREATED)


class KYCAdminReviewView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=['KYC'],
        summary='[Admin] List all KYC submissions',
        responses={200: s.KYCSerializer(many=True)}
    )
    def get(self, request):
        status_filter = request.query_params.get('status')
        qs = m.KYC.objects.select_related('user').all()
        if status_filter:
            qs = qs.filter(verification_status=status_filter.upper())
        return Response(s.KYCSerializer(qs, many=True).data)


class KYCAdminDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get_object(self, pk):
        try:
            return m.KYC.objects.get(pk=pk)
        except m.KYC.DoesNotExist:
            return None

    @extend_schema(
        tags=['KYC'],
        summary='[Admin] Approve or reject a KYC submission',
        request=s.KYCAdminUpdateSerializer,
        responses={
            200: s.KYCSerializer,
            400: OpenApiResponse(description='Validation error'),
            404: OpenApiResponse(description='KYC not found'),
        }
    )
    def patch(self, request, pk):
        kyc = self.get_object(pk)
        if not kyc:
            return Response({"detail": "KYC not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = s.KYCAdminUpdateSerializer(kyc, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(s.KYCSerializer(kyc).data)


# ── Transaction PIN ───────────────────────────────────────────────────────────

class SetPINView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['PIN'],
        summary='Set a new transaction PIN',
        request=s.SetPINSerializer,
        responses={
            200: OpenApiResponse(description='PIN set successfully.'),
            400: OpenApiResponse(description='Validation error or PIN already set.'),
        }
    )
    def post(self, request):
        if request.user.transaction_pin:
            return Response(
                {"detail": "PIN already set. Use change-pin to update it."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = s.SetPINSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_transaction_pin(serializer.validated_data['pin'])
        return Response({"message": "Transaction PIN set successfully."})


class ChangePINView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['PIN'],
        summary='Change existing transaction PIN',
        request=s.ChangePINSerializer,
        responses={
            200: OpenApiResponse(description='PIN changed successfully.'),
            400: OpenApiResponse(description='Wrong current PIN or validation error.'),
        }
    )
    def post(self, request):
        if not request.user.transaction_pin:
            return Response(
                {"detail": "No PIN set. Use set-pin first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = s.ChangePINSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_transaction_pin(serializer.validated_data['current_pin']):
            return Response({"detail": "Current PIN is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_transaction_pin(serializer.validated_data['new_pin'])
        return Response({"message": "Transaction PIN changed successfully."})


class VerifyPINView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['PIN'],
        summary='Verify transaction PIN (e.g. before a transaction)',
        request=s.VerifyPINSerializer,
        responses={
            200: OpenApiResponse(description='PIN is valid.'),
            400: OpenApiResponse(description='PIN is invalid or not set.'),
        }
    )
    def post(self, request):
        if not request.user.transaction_pin:
            return Response({"detail": "No PIN set."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = s.VerifyPINSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.user.check_transaction_pin(serializer.validated_data['pin']):
            return Response({"valid": True, "message": "PIN verified successfully."})
        return Response({"valid": False, "detail": "Invalid PIN."}, status=status.HTTP_400_BAD_REQUEST)
