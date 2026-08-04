from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import Permission, Role
from .serializers import PermissionSerializer, RoleSerializer


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """The permission catalog (module x tier) is fixed by migrations, so this is read-only."""

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAdminUser]


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=["post"])
    def add_user(self, request, pk=None):
        role = self.get_object()
        user = get_object_or_404(User, pk=request.data.get("user_id"))
        role.users.add(user)
        return Response(self.get_serializer(role).data)

    @action(detail=True, methods=["post"])
    def remove_user(self, request, pk=None):
        role = self.get_object()
        user = get_object_or_404(User, pk=request.data.get("user_id"))
        role.users.remove(user)
        return Response(self.get_serializer(role).data)

    @action(detail=True, methods=["post"])
    def add_permission(self, request, pk=None):
        role = self.get_object()
        permission = get_object_or_404(Permission, pk=request.data.get("permission_id"))
        role.permissions.add(permission)
        return Response(self.get_serializer(role).data)

    @action(detail=True, methods=["post"])
    def remove_permission(self, request, pk=None):
        role = self.get_object()
        permission = get_object_or_404(Permission, pk=request.data.get("permission_id"))
        role.permissions.remove(permission)
        return Response(self.get_serializer(role).data)
