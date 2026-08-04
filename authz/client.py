from contextlib import contextmanager

from django.conf import settings
from openfga_sdk.client import ClientConfiguration
from openfga_sdk.client.models import (
    ClientCheckRequest,
    ClientListObjectsRequest,
    ClientTuple,
    ClientWriteRequest,
)
from openfga_sdk.exceptions import ApiException
from openfga_sdk.sync import OpenFgaClient


def user_key(user_id):
    return f"user:{user_id}"


def object_key(object_type, object_id):
    return f"{object_type}:{object_id}"


def role_assignee_key(role_id):
    return f"role:{role_id}#assignee"


@contextmanager
def get_client():
    configuration = ClientConfiguration(
        api_url=settings.OPENFGA_API_URL,
        store_id=settings.OPENFGA_STORE_ID,
        authorization_model_id=settings.OPENFGA_AUTHORIZATION_MODEL_ID,
    )
    with OpenFgaClient(configuration) as client:
        yield client


def write_tuple(user, relation, obj, ignore_conflict=False):
    with get_client() as client:
        try:
            client.write(ClientWriteRequest(writes=[ClientTuple(user=user, relation=relation, object=obj)]))
        except ApiException as exc:
            if not (ignore_conflict and "already exists" in exc.error_message.lower()):
                raise


def delete_tuple(user, relation, obj, ignore_missing=False):
    with get_client() as client:
        try:
            client.write(ClientWriteRequest(deletes=[ClientTuple(user=user, relation=relation, object=obj)]))
        except ApiException as exc:
            if not (ignore_missing and "does not exist" in exc.error_message.lower()):
                raise


def check(user_id, relation, object_type, object_id):
    with get_client() as client:
        response = client.check(
            ClientCheckRequest(
                user=user_key(user_id),
                relation=relation,
                object=object_key(object_type, object_id),
            )
        )
    return bool(response.allowed)


def accessible_object_ids(user_id, object_type, relation="can_view"):
    with get_client() as client:
        response = client.list_objects(
            ClientListObjectsRequest(
                user=user_key(user_id),
                relation=relation,
                type=object_type,
            )
        )
    return [int(obj.split(":", 1)[1]) for obj in response.objects]


def grant_owner(object_type, object_id, user_id, ignore_conflict=False):
    write_tuple(user_key(user_id), "owner", object_key(object_type, object_id), ignore_conflict=ignore_conflict)


def revoke_owner(object_type, object_id, user_id):
    delete_tuple(user_key(user_id), "owner", object_key(object_type, object_id), ignore_missing=True)


def set_parent(object_type, object_id, parent_type, parent_id, ignore_conflict=False):
    write_tuple(
        object_key(parent_type, parent_id),
        "parent",
        object_key(object_type, object_id),
        ignore_conflict=ignore_conflict,
    )


def assign_role_permission(role_id, module_name, relation):
    write_tuple(role_assignee_key(role_id), relation, object_key("module", module_name), ignore_conflict=True)


def revoke_role_permission(role_id, module_name, relation):
    delete_tuple(role_assignee_key(role_id), relation, object_key("module", module_name), ignore_missing=True)


def assign_user_role(role_id, user_id):
    write_tuple(user_key(user_id), "assignee", object_key("role", role_id), ignore_conflict=True)


def revoke_user_role(role_id, user_id):
    delete_tuple(user_key(user_id), "assignee", object_key("role", role_id), ignore_missing=True)
