from openfga_sdk import (
    Metadata,
    ObjectRelation,
    RelationMetadata,
    RelationReference,
    TupleToUserset,
    TypeDefinition,
    Userset,
    Usersets,
    WriteAuthorizationModelRequest,
)

# Modules are the RBAC-level resources: a Role grants a permission tier on a
# whole module (e.g. "documents"), which every object of that type inherits
# via its "parent" link, on top of any direct per-object share at that tier.
MODULES = ["documents", "projects"]

# Ordered low -> high. Each tier implies everything before it
# (can_admin implies can_delete implies can_edit implies can_view).
PERMISSION_TIERS = ["can_view", "can_edit", "can_delete", "can_admin"]


def _this():
    return Userset(this={})


def _computed(relation):
    return Userset(computed_userset=ObjectRelation(object="", relation=relation))


def _from_parent(relation):
    return Userset(
        tuple_to_userset=TupleToUserset(
            tupleset=ObjectRelation(object="", relation="parent"),
            computed_userset=ObjectRelation(object="", relation=relation),
        )
    )


def _union(*children):
    return Userset(union=Usersets(child=list(children)))


def _module_type():
    """Module tiers are only ever role-granted (no direct per-object owner concept)."""
    relations = {}
    for i, tier in enumerate(PERMISSION_TIERS):
        if i == len(PERMISSION_TIERS) - 1:
            relations[tier] = _this()
        else:
            relations[tier] = _union(_this(), _computed(PERMISSION_TIERS[i + 1]))

    return TypeDefinition(
        type="module",
        relations=relations,
        metadata=Metadata(
            relations={
                tier: RelationMetadata(
                    directly_related_user_types=[RelationReference(type="role", relation="assignee")]
                )
                for tier in PERMISSION_TIERS
            }
        ),
    )


def _resource_type(type_name):
    relations = {"parent": _this(), "owner": _this()}
    metadata_relations = {
        "parent": RelationMetadata(directly_related_user_types=[RelationReference(type="module")]),
        "owner": RelationMetadata(directly_related_user_types=[RelationReference(type="user")]),
    }

    for i, tier in enumerate(PERMISSION_TIERS):
        implied_by = "owner" if i == len(PERMISSION_TIERS) - 1 else PERMISSION_TIERS[i + 1]
        relations[tier] = _union(_this(), _computed(implied_by), _from_parent(tier))
        metadata_relations[tier] = RelationMetadata(directly_related_user_types=[RelationReference(type="user")])

    return TypeDefinition(
        type=type_name,
        relations=relations,
        metadata=Metadata(relations=metadata_relations),
    )


def build_authorization_model():
    role_type = TypeDefinition(
        type="role",
        relations={"assignee": _this()},
        metadata=Metadata(
            relations={
                "assignee": RelationMetadata(directly_related_user_types=[RelationReference(type="user")]),
            }
        ),
    )

    return WriteAuthorizationModelRequest(
        schema_version="1.1",
        type_definitions=[
            TypeDefinition(type="user"),
            role_type,
            _module_type(),
            _resource_type("document"),
            _resource_type("project"),
        ],
    )
