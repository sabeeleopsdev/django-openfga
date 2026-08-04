from django.conf import settings
from django.db import models

from .model import MODULES, PERMISSION_TIERS

MODULE_CHOICES = [(name, name.capitalize()) for name in MODULES]

_TIER_LABELS = {
    "can_view": "Can view",
    "can_edit": "Can edit",
    "can_delete": "Can delete",
    "can_admin": "Full control",
}
RELATION_CHOICES = [(tier, _TIER_LABELS[tier]) for tier in PERMISSION_TIERS]


class Permission(models.Model):
    module = models.CharField(max_length=50, choices=MODULE_CHOICES)
    relation = models.CharField(max_length=20, choices=RELATION_CHOICES)

    class Meta:
        unique_together = ("module", "relation")
        ordering = ["module", "relation"]

    def __str__(self):
        return f"{self.module}.{self.relation}"


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="roles", blank=True)

    def __str__(self):
        return self.name
