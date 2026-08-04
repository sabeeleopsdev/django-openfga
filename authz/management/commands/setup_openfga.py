import re

from django.conf import settings
from django.core.management.base import BaseCommand
from openfga_sdk import CreateStoreRequest
from openfga_sdk.client import ClientConfiguration
from openfga_sdk.sync import OpenFgaClient

from authz import client as fga_client
from authz.model import MODULES, build_authorization_model

STORE_NAME = "django-openfga-demo"
ENV_PATH = settings.BASE_DIR / ".env"

# Relation names retired by earlier versions of the model. Any tuple still
# using these no longer matches anything in the current model and is dead
# weight, so we proactively clean them up whenever the model changes.
RETIRED_RELATIONS = ["viewer", "editor"]


def _update_env_file(store_id, model_id):
    if not ENV_PATH.exists():
        ENV_PATH.write_text("")

    lines = ENV_PATH.read_text().splitlines()
    values = {"OPENFGA_STORE_ID": store_id, "OPENFGA_AUTHORIZATION_MODEL_ID": model_id}
    seen = set()

    for i, line in enumerate(lines):
        match = re.match(r"^(OPENFGA_STORE_ID|OPENFGA_AUTHORIZATION_MODEL_ID)=", line)
        if match:
            key = match.group(1)
            lines[i] = f"{key}={values[key]}"
            seen.add(key)

    for key, value in values.items():
        if key not in seen:
            lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(lines) + "\n")


class Command(BaseCommand):
    help = (
        "Creates (or reuses) the OpenFGA store, writes the authorization model, "
        "backfills module parent tuples for existing objects, and updates .env"
    )

    def handle(self, *args, **options):
        base_configuration = ClientConfiguration(api_url=settings.OPENFGA_API_URL)

        with OpenFgaClient(base_configuration) as client:
            existing = next(
                (s for s in client.list_stores().stores if s.name == STORE_NAME),
                None,
            )
            if existing:
                store_id = existing.id
                self.stdout.write(f"Reusing existing store '{STORE_NAME}': {store_id}")
            else:
                store = client.create_store(CreateStoreRequest(name=STORE_NAME))
                store_id = store.id
                self.stdout.write(f"Created store '{STORE_NAME}': {store_id}")

        store_configuration = ClientConfiguration(api_url=settings.OPENFGA_API_URL, store_id=store_id)
        with OpenFgaClient(store_configuration) as client:
            model_response = client.write_authorization_model(build_authorization_model())
            model_id = model_response.authorization_model_id
            self.stdout.write(f"Wrote authorization model: {model_id}")

        _update_env_file(store_id, model_id)

        settings.OPENFGA_STORE_ID = store_id
        settings.OPENFGA_AUTHORIZATION_MODEL_ID = model_id
        self._backfill_parent_tuples()
        self._resync_role_permission_tuples()

        self.stdout.write(self.style.SUCCESS(
            f"Updated {ENV_PATH} with OPENFGA_STORE_ID and OPENFGA_AUTHORIZATION_MODEL_ID.\n"
            "Restart the web container so it picks up the new environment variables."
        ))

    def _backfill_parent_tuples(self):
        from documents.models import Document
        from projects.models import Project

        for document in Document.objects.all():
            fga_client.set_parent("document", document.id, "module", "documents", ignore_conflict=True)
        for project in Project.objects.all():
            fga_client.set_parent("project", project.id, "module", "projects", ignore_conflict=True)

        self.stdout.write("Backfilled module parent tuples for existing documents and projects.")

    def _resync_role_permission_tuples(self):
        from authz.models import Role

        for role in Role.objects.prefetch_related("permissions"):
            for module in MODULES:
                for old_relation in RETIRED_RELATIONS:
                    fga_client.revoke_role_permission(role.id, module, old_relation)
            for permission in role.permissions.all():
                fga_client.assign_role_permission(role.id, permission.module, permission.relation)

        self.stdout.write("Resynced role permission tuples to the current relation names.")
