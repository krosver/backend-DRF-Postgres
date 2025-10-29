from django.conf import settings
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import User
from .serializers import RegisterSerializer, UserSerializer

from core.auth import (
    check_password,
    make_access_and_refresh,
    create_session,
    set_session_cookie,
    revoke_session,
    revoke_jwt,
)
from core.models import Session


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        if not email or not password:
            return Response({"detail": "email and password required"}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(email=email, is_active=True).first()
        if not user or not check_password(password, user.password_hash):
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        access, refresh = make_access_and_refresh(user.id)
        session = create_session(user, request.META)
        response = Response({"access": access, "refresh": refresh}, status=status.HTTP_200_OK)
        set_session_cookie(response, session)
        return response


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
        sessionid = request.COOKIES.get(cookie_name)
        if sessionid:
            revoke_session(sessionid)
        auth = getattr(request, "auth", None)
        if isinstance(auth, dict) and auth.get("type") == "jwt":
            payload = auth.get("payload") or {}
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                revoke_jwt(jti, exp)
        response = Response({"detail": "Logged out"}, status=status.HTTP_200_OK)
        response.delete_cookie(cookie_name)
        return response


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        allowed_fields = {"first_name", "last_name", "middle_name"}
        payload = {k: v for k, v in request.data.items() if k in allowed_fields}
        serializer = UserSerializer(request.user, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request):
        user = request.user
        user.is_active = False
        user.save()
        Session.objects.filter(user=user).delete()
        response = Response({"detail": "Account deactivated"}, status=status.HTTP_200_OK)
        response.delete_cookie(getattr(settings, "SESSION_COOKIE_NAME", "sessionid"))
        return response
