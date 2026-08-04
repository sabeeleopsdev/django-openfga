from rest_framework.permissions import IsAuthenticated

from authz.viewsets import OwnedObjectViewSet

from .models import Project
from .permissions import ProjectPermission
from .serializers import ProjectSerializer


class ProjectViewSet(OwnedObjectViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, ProjectPermission]
    object_type = "project"
    module_name = "projects"
