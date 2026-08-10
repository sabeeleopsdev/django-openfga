import json
import subprocess
from pathlib import Path

from openfga_sdk import WriteAuthorizationModelRequest

# Modules are the RBAC-level resources: a Role grants a permission tier on a
# whole module (e.g. "documents"), which every object of that type inherits
# via its "parent" link, on top of any direct per-object share at that tier.
# These are app-level instance names, not part of the OpenFGA schema itself,
# so they aren't derivable from model.fga.
MODULES = ["documents", "projects"]

# Ordered low -> high. Each tier implies everything before it
# (can_admin implies can_delete implies can_edit implies can_view). Kept in
# sync by hand with the tiers defined on the "module" type in model.fga.
PERMISSION_TIERS = ["can_view", "can_edit", "can_delete", "can_admin"]

MODEL_FILE = Path(__file__).parent / "model.fga"


def build_authorization_model():
    """Loads authz/model.fga (the DSL, and single source of truth for the
    OpenFGA schema) and transforms it into a WriteAuthorizationModelRequest
    via the `fga` CLI, which understands the DSL grammar.
    """
    try:
        result = subprocess.run(
            ["fga", "model", "transform", "--file", str(MODEL_FILE), "--output-format", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "The `fga` CLI is required to load authz/model.fga but was not found on PATH. "
            "It's installed automatically in the app's Docker image."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Failed to parse {MODEL_FILE}:\n{exc.stderr}") from exc

    model = json.loads(result.stdout)

    return WriteAuthorizationModelRequest(
        schema_version=model["schema_version"],
        type_definitions=model["type_definitions"],
        conditions=model.get("conditions"),
    )
