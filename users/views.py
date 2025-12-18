from django.contrib.auth import authenticate
from django.conf import settings
from django.http import HttpRequest

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework import status, permissions

from users import serializers as user_serializers
from users import models as user_models


class RegisterView(APIView):
    def post(self, request):
        serializer = user_serializers.UserRegisterSerializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            user = serializer.save()

            refresh = RefreshToken.for_user(user)

            response_data = {
                'access': str(refresh.access_token),
                'message': "User registered and logged in successfully"
            }

            response = Response(response_data, status=status.HTTP_201_CREATED)

            response.set_cookie(
                key="refresh",
                value=str(refresh),
                httponly=True,
                max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
                samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
                secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', not settings.DEBUG),
            )

            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error", "Please provide both email and password"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=email, password=password)

        if user:
            refresh = RefreshToken.for_user(user)

            response_data = {
                'access': str(refresh.access_token),
            }

            response = Response(response_data, status=status.HTTP_200_OK)

            response.set_cookie(
                key="refresh",
                value=str(refresh),
                httponly=True,
                max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
                samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
                secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', not settings.DEBUG),
            )

            return response

        return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh")

        if not refresh_token:
            return Response({"error", "Refresh token not found"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            response = Response({"message", "Logout successful"}, status=status.HTTP_200_OK)
            response.delete_cookie("refresh")

            return response
        except (TokenError, InvalidToken):
            return Response({"error", "Invalid or expired refresh token"}, status=status.HTTP_400_BAD_REQUEST)


class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = user_serializers.UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CookieTokenRefreshSerializer(TokenRefreshSerializer):
    """
    This custom serializer reads the refresh token from the httpOnly cookie.
    """
    # We don’t expect the client to send 'refresh' in the body; we'll inject it from the request cookie
    refresh = None  # We will get it from the request context instead.

    def validate(self, attrs):
        # Pull the refresh token from the request's cookies and place it into attrs so parent logic works
        attrs['refresh'] = self.context['request'].COOKIES.get('refresh', None)

        # If there’s no cookie, we can’t refresh—throw a clear error
        if attrs['refresh'] is None:
            raise InvalidToken('No valid refresh token found in cookie.')

        # Delegate the rest (signature checks, expiry, rotation logic) to the parent serializer
        return super().validate(attrs)
