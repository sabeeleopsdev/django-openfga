from django.db.models.signals import m2m_changed, pre_delete
from django.dispatch import receiver

from . import client
from .models import Permission, Role


@receiver(m2m_changed, sender=Role.permissions.through)
def sync_role_permissions(sender, instance, action, pk_set, reverse, **kwargs):
    if reverse or action not in ("pre_clear", "post_add", "post_remove"):
        return

    if action == "pre_clear":
        for permission in instance.permissions.all():
            client.revoke_role_permission(instance.id, permission.module, permission.relation)
        return

    for permission in Permission.objects.filter(pk__in=pk_set):
        if action == "post_add":
            client.assign_role_permission(instance.id, permission.module, permission.relation)
        else:
            client.revoke_role_permission(instance.id, permission.module, permission.relation)


@receiver(m2m_changed, sender=Role.users.through)
def sync_role_users(sender, instance, action, pk_set, reverse, **kwargs):
    if reverse or action not in ("pre_clear", "post_add", "post_remove"):
        return

    if action == "pre_clear":
        for user in instance.users.all():
            client.revoke_user_role(instance.id, user.id)
        return

    for user_id in pk_set:
        if action == "post_add":
            client.assign_user_role(instance.id, user_id)
        else:
            client.revoke_user_role(instance.id, user_id)


@receiver(pre_delete, sender=Role)
def cleanup_role_tuples(sender, instance, **kwargs):
    for permission in instance.permissions.all():
        client.revoke_role_permission(instance.id, permission.module, permission.relation)
    for user in instance.users.all():
        client.revoke_user_role(instance.id, user.id)
