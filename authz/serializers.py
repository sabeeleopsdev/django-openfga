from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Permission, Role


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "module", "relation"]
        read_only_fields = fields


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        source="permissions", queryset=Permission.objects.all(), many=True, write_only=True, required=False
    )
    users = serializers.SlugRelatedField(slug_field="username", many=True, read_only=True)
    user_ids = serializers.PrimaryKeyRelatedField(
        source="users", queryset=User.objects.all(), many=True, write_only=True, required=False
    )

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions", "permission_ids", "users", "user_ids"]
