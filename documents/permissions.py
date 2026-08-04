from authz.permissions import ObjectPermission


class DocumentPermission(ObjectPermission):
    object_type = "document"
