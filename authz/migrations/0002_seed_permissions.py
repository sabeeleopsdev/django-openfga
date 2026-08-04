from django.db import migrations

from authz.model import MODULES

RELATIONS = ["viewer", "editor"]


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("authz", "Permission")
    for module in MODULES:
        for relation in RELATIONS:
            Permission.objects.get_or_create(module=module, relation=relation)


def remove_permissions(apps, schema_editor):
    Permission = apps.get_model("authz", "Permission")
    Permission.objects.filter(module__in=MODULES, relation__in=RELATIONS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authz", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_permissions, remove_permissions),
    ]
