from rest_framework import serializers

from authz import client

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source="created_by.username")

    class Meta:
        model = Document
        fields = ["id", "title", "content", "created_by"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and not client.check(request.user.id, "can_edit", "document", instance.id):
            data["content"] = None
        return data
