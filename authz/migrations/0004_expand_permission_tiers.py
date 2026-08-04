from django.db import migrations

from authz.model import MODULES

RENAME_MAP = {"viewer": "can_view", "editor": "can_edit"}
NEW_TIERS = ["can_delete", "can_admin"]


def forwards(apps, schema_editor):
    Permission = apps.get_model("authz", "Permission")
    for old, new in RENAME_MAP.items():
        Permission.objects.filter(relation=old).update(relation=new)

    for module in MODULES:
        for relation in NEW_TIERS:
            Permission.objects.get_or_create(module=module, relation=relation)


def backwards(apps, schema_editor):
    Permission = apps.get_model("authz", "Permission")
    Permission.objects.filter(relation__in=NEW_TIERS).delete()
    for old, new in RENAME_MAP.items():
        Permission.objects.filter(relation=new).update(relation=old)


class Migration(migrations.Migration):

    dependencies = [
        ("authz", "0003_alter_permission_relation"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
