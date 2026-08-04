from django.apps import AppConfig


class AuthzConfig(AppConfig):
    name = "authz"

    def ready(self):
        from . import signals  # noqa: F401
