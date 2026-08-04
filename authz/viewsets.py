from rest_framework import viewsets

from . import client


class OwnedObjectViewSet(viewsets.ModelViewSet):
    """
    Base for modules with per-object ownership + module-wide RBAC.
    Subclasses set: queryset, serializer_class, permission_classes, object_type, module_name.
    """

    object_type = None
    module_name = None

    def get_queryset(self):
        model = self.queryset.model
        accessible_ids = client.accessible_object_ids(self.request.user.id, self.object_type, relation="can_view")
        return model.objects.filter(pk__in=accessible_ids)

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user)
        client.grant_owner(self.object_type, obj.id, self.request.user.id)
        client.set_parent(self.object_type, obj.id, "module", self.module_name)

    def perform_destroy(self, instance):
        object_id = instance.id
        owner_id = instance.created_by_id
        instance.delete()
        client.revoke_owner(self.object_type, object_id, owner_id)
