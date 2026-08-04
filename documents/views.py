from rest_framework.permissions import IsAuthenticated

from authz.viewsets import OwnedObjectViewSet

from .models import Document
from .permissions import DocumentPermission
from .serializers import DocumentSerializer


class DocumentViewSet(OwnedObjectViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, DocumentPermission]
    object_type = "document"
    module_name = "documents"
