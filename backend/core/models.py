# core/models.py
from django.db import models
from django.utils import timezone


class Session(models.Model):

    id = models.CharField(primary_key=True, max_length=64)  # sessionid, UUID или hex
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    expire_at = models.DateTimeField(db_index=True)
    user_agent = models.CharField(max_length=256, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    def is_expired(self) -> bool:
        return timezone.now() >= self.expire_at

    def __str__(self):
        return f"Session<{self.id}> for {self.user.email}"


class RevokedToken(models.Model):
    
    jti = models.CharField(max_length=36, unique=True)  # JWT ID
    exp = models.DateTimeField()  # срок истечения токена
    revoked_at = models.DateTimeField(default=timezone.now)

    def is_active(self) -> bool:
        return timezone.now() < self.exp

    def __str__(self):
        return f"RevokedToken<{self.jti}>"
