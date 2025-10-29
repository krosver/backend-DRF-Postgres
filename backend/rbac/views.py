# rbac/views.py
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from .models import Role, Resource, PermissionRule, UserRole
from .serializers import RoleSerializer, ResourceSerializer, PermissionRuleSerializer, UserRoleSerializer

def is_admin(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_staff", False):
        return True
    return UserRole.objects.filter(user=user, role__name__iexact="admin").exists()

class AdminOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_admin(request.user)

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [AdminOnly]

class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [AdminOnly]

class PermissionRuleViewSet(viewsets.ModelViewSet):
    queryset = PermissionRule.objects.select_related("role","resource").all()
    serializer_class = PermissionRuleSerializer
    permission_classes = [AdminOnly]

    @action(detail=False, methods=["get"], permission_classes=[AdminOnly])
    def by_role(self, request):
        role = request.query_params.get("role")
        qs = self.get_queryset()
        if role:
            qs = qs.filter(role__name__iexact=role)
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        return self.get_paginated_response(ser.data) if page is not None else Response(ser.data)

class UserRoleViewSet(viewsets.ModelViewSet):
    queryset = UserRole.objects.select_related("role").all()
    serializer_class = UserRoleSerializer
    permission_classes = [AdminOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        uid = self.request.query_params.get("user_id")
        if uid:
            qs = qs.filter(user_id=uid)
        return qs

    def perform_create(self, serializer):
        user_id = self.request.data.get("user_id")
        serializer.save(user_id=user_id)
