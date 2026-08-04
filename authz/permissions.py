from rest_framework.permissions import SAFE_METHODS, BasePermission

from . import client


class ObjectPermission(BasePermission):
    """Object-level permission backed by OpenFGA. Subclasses set object_type."""

    object_type = None

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            relation = "can_view"
        elif request.method == "DELETE":
            relation = "can_delete"
        else:
            relation = "can_edit"
        return client.check(request.user.id, relation, self.object_type, obj.id)
