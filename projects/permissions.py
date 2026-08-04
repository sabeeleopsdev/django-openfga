from authz.permissions import ObjectPermission


class ProjectPermission(ObjectPermission):
    object_type = "project"
