# rbac/serializers.py
from rest_framework import serializers
from .models import Role, Resource, PermissionRule, UserRole

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "name", "description")

class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ("id", "code", "description")

class PermissionRuleSerializer(serializers.ModelSerializer):
    role = serializers.SlugRelatedField(slug_field="name", queryset=Role.objects.all())
    resource = serializers.SlugRelatedField(slug_field="code", queryset=Resource.objects.all())

    class Meta:
        model = PermissionRule
        fields = (
            "id","role","resource",
            "read","read_all","create","update","update_all","delete","delete_all",
        )

class UserRoleSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    role = serializers.SlugRelatedField(slug_field="name", queryset=Role.objects.all())

    class Meta:
        model = UserRole
        fields = ("id","user","role")
