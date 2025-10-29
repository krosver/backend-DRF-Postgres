# rbac/models.py
from django.db import models

USER_FK = "users.User"

class Role(models.Model):
    name = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=256, blank=True)

    def __str__(self):
        return self.name

class Resource(models.Model):
    code = models.CharField(max_length=64, unique=True)  # например: "users", "rbac.rules", "orders"
    description = models.CharField(max_length=256, blank=True)

    def __str__(self):
        return self.code

class PermissionRule(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="rules")
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="rules")

    read = models.BooleanField(default=False)
    read_all = models.BooleanField(default=False)
    create = models.BooleanField(default=False)
    update = models.BooleanField(default=False)
    update_all = models.BooleanField(default=False)
    delete = models.BooleanField(default=False)
    delete_all = models.BooleanField(default=False)

    class Meta:
        unique_together = ("role", "resource")

    def __str__(self):
        return f"{self.role}:{self.resource}"

class UserRole(models.Model):
    user = models.ForeignKey(USER_FK, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")

    class Meta:
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user_id}:{self.role.name}"
