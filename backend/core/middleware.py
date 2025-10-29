# core/middleware.py
from typing import Optional
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from django.http import HttpRequest

from core import auth as core_auth
from users.models import User

import logging
logger = logging.getLogger(__name__)

class AuthMiddleware(MiddlewareMixin):

    def _user_from_session_cookie(self, request: HttpRequest) -> Optional[User]:
        sid = request.COOKIES.get(getattr(settings, "SESSION_COOKIE_NAME", "sessionid"))
        if not sid:
            return None
        user = core_auth.get_user_from_session(sid)
        if user:
            session = core_auth.get_session(sid)
            request.auth = {"type": "session", "session": session}
        return user

    def _user_from_bearer(self, request: HttpRequest) -> Optional[User]:
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header:
            return None
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        token = parts[1].strip()
        
        user = core_auth.get_user_from_jwt(token)
        if user:
            try:
                payload = core_auth.parse_jwt(token)
            except core_auth.AuthError:
                payload = None
            request.auth = {"type": "jwt", "payload": payload, "token": token}
        return user

    def process_request(self, request: HttpRequest):
        request.user = AnonymousUser()
        request.auth = None

        user = self._user_from_session_cookie(request)

        if not user:
            user = self._user_from_bearer(request)

        if user:
            request.user = user

