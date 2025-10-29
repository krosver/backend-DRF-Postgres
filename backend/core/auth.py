
import secrets
import bcrypt
import jwt
import uuid
from datetime import timedelta, datetime
from typing import Optional, Tuple, Dict, Any

from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse

from rest_framework.authentication import BaseAuthentication
from django.contrib.auth.models import AnonymousUser

from core.models import Session, RevokedToken
from users.models import User

JWT_ALGORITHM = getattr(settings, "JWT_ALGORITHM", "HS256")
JWT_ACCESS_TTL_MIN = int(getattr(settings, "JWT_ACCESS_TTL_MIN", 15))
JWT_REFRESH_TTL_MIN = int(getattr(settings, "JWT_REFRESH_TTL_MIN", 60 * 24 * 30))
SESSION_TTL_MIN = int(getattr(settings, "SESSION_TTL_MIN", 60 * 24 * 30))
SESSION_COOKIE_NAME = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
SESSION_COOKIE_SECURE = getattr(settings, "SESSION_COOKIE_SECURE", True)
SESSION_COOKIE_HTTPONLY = getattr(settings, "SESSION_COOKIE_HTTPONLY", True)
SESSION_COOKIE_SAMESITE = getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax")


class AuthError(Exception):
    pass


def hash_password(raw: str) -> str:
    """Возвращает bcrypt-хеш для строки пароля."""
    if raw is None:
        raise ValueError("raw password required")
    hashed = bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def check_password(raw: str, hashed: str) -> bool:
    """Проверяет пароль против bcrypt-хеша."""
    if not raw or not hashed:
        return False
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _now_utc() -> datetime:
    return datetime.utcnow()


def make_jwt(user_id: int, minutes: int = JWT_ACCESS_TTL_MIN, typ: str = "access") -> str:
    iat = _now_utc()
    exp = iat + timedelta(minutes=int(minutes))
    payload = {
        "sub": str(user_id),
        "typ": typ,
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def parse_jwt(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthError("token_expired")
    except jwt.InvalidTokenError:
        raise AuthError("invalid_token")
    jti = payload.get("jti")
    if jti and is_jwt_revoked(jti):
        raise AuthError("token_revoked")
    return payload


def make_access_and_refresh(user_id: int) -> Tuple[str, str]:
    access = make_jwt(user_id, minutes=JWT_ACCESS_TTL_MIN, typ="access")
    refresh = make_jwt(user_id, minutes=JWT_REFRESH_TTL_MIN, typ="refresh")
    return access, refresh


def revoke_jwt(jti: str, exp_timestamp: int) -> None:
    try:
        exp_dt = datetime.fromtimestamp(int(exp_timestamp), tz=timezone.utc)
    except Exception:
        exp_dt = timezone.now()
    RevokedToken.objects.get_or_create(jti=jti, defaults={"exp": exp_dt})


def is_jwt_revoked(jti: str) -> bool:
    return RevokedToken.objects.filter(jti=jti).exists()


def create_session(user: User, request_meta: Optional[dict] = None, ttl_min: int = SESSION_TTL_MIN) -> Session:
    sid = secrets.token_hex(32)
    now = timezone.now()
    expire_at = now + timedelta(minutes=int(ttl_min))
    ua = None
    ip = None
    if request_meta:
        ua = request_meta.get("HTTP_USER_AGENT", "")[:255]
        xf = request_meta.get("HTTP_X_FORWARDED_FOR")
        if xf:
            ip = xf.split(",")[0].strip()
        else:
            ip = request_meta.get("REMOTE_ADDR")
    session = Session.objects.create(id=sid, user=user, created_at=now, expire_at=expire_at, user_agent=ua or "", ip=ip)
    return session


def set_session_cookie(response: HttpResponse, session: Session) -> None:
    expires = session.expire_at
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.id,
        expires=expires,
        httponly=SESSION_COOKIE_HTTPONLY,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
    )


def revoke_session(session_id: str) -> None:
    Session.objects.filter(id=session_id).delete()


def get_session(session_id: str) -> Optional[Session]:
    return Session.objects.filter(id=session_id, expire_at__gt=timezone.now()).select_related("user").first()


def get_user_from_jwt(token: str) -> Optional[User]:
    try:
        payload = parse_jwt(token)
    except AuthError:
        return None
    if payload.get("typ") != "access":
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    return User.objects.filter(pk=sub, is_active=True).first()


def get_user_from_session(session_id: str) -> Optional[User]:
    sess = get_session(session_id)
    if not sess:
        return None
    user = sess.user
    if not user.is_active or getattr(user, "deleted_at", None):
        return None
    return user


class MiddlewareAuth(BaseAuthentication):
    def authenticate(self, request) -> Optional[Tuple[User, Any]]:
        u = getattr(request._request, "user", None)
        if u and not isinstance(u, AnonymousUser):
            return (u, getattr(request._request, "auth", None))
        return None