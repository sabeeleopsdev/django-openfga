# django-openfga-demo

A reference project showing how to wire [OpenFGA](https://openfga.dev/) into a Django + Django REST Framework backend: JWT login, per-object sharing, and role-based access control (RBAC) — all resolved through a single OpenFGA authorization model.

## Stack

- Django 6 + Django REST Framework
- `djangorestframework-simplejwt` for login
- `drf-spectacular` for OpenAPI/Swagger docs
- OpenFGA (server + Python SDK) for authorization
- Postgres (one DB for the app, a separate one for OpenFGA's own storage)
- docker-compose for local orchestration

## Authorization model

Two patterns, resolved through the same relations:

1. **Per-object sharing** — each resource (`document`, `project`) has a permission hierarchy: `can_view → can_edit → can_delete → can_admin`, each tier implying the ones below it. The creator of an object is its `owner`, which grants the full chain on that object.
2. **RBAC** — a `role` type plus one `module` type per resource type (e.g. `module:documents`). A `Role` (a normal Django model, manageable via admin or the REST API) grants a tier on a whole module; every object of that type inherits it through a `parent` link using OpenFGA's `X from parent` relation. Assigning a role once applies across every object of that type — no per-object tuple per user needed.

These two paths are just OR'd together per relation, so a user gets a tier if *either* path resolves true — e.g. someone whose role only grants `can_view` module-wide can still fully edit a document they personally own.

The model lives as OpenFGA DSL in [`authz/model.fga`](authz/model.fga) — this file is the single source of truth for the schema:

```
model
  schema 1.1

type user

type role
  relations
    define assignee: [user]

type module
  relations
    define can_admin: [role#assignee]
    define can_delete: [role#assignee] or can_admin
    define can_edit: [role#assignee] or can_delete
    define can_view: [role#assignee] or can_edit

type document
  relations
    define parent: [module]
    define owner: [user]
    define can_admin: [user] or owner or can_admin from parent
    define can_delete: [user] or can_admin or can_delete from parent
    define can_edit: [user] or can_delete or can_edit from parent
    define can_view: [user] or can_edit or can_view from parent

type project
  relations
    define parent: [module]
    define owner: [user]
    define can_admin: [user] or owner or can_admin from parent
    define can_delete: [user] or can_admin or can_delete from parent
    define can_edit: [user] or can_delete or can_edit from parent
    define can_view: [user] or can_edit or can_view from parent
```

### Changing the model

Whenever you edit a relation, add a new one, or add a new type in `authz/model.fga`:

```bash
docker compose exec web python manage.py setup_openfga
docker compose up -d web
```

`setup_openfga` is idempotent and safe to re-run any time: it reads `authz/model.fga` through the [`fga` CLI](https://github.com/openfga/cli) (`fga model transform`, which turns the DSL into the JSON the OpenFGA API expects), writes it as a new model version on the existing store, backfills `parent` tuples for any objects created before the change, and resyncs every Role's OpenFGA tuples to the current relation names (so a relation rename doesn't leave stale tuples behind). The `fga` CLI is preinstalled in the `web` image (see the `Dockerfile`), so no local install is needed to run it inside the container.

Use `docker compose up -d web`, not `docker compose restart web`, afterwards — `restart` reuses the container's existing environment, so it won't pick up the new `OPENFGA_AUTHORIZATION_MODEL_ID` that `setup_openfga` just wrote to `.env`. Only `up -d` re-reads `env_file` and recreates the container with it.

If you add a brand-new permission tier (not just edit existing relations), also update `PERMISSION_TIERS` in [`authz/model.py`](authz/model.py) — it drives the Django-side `Role`/`Permission` choices and isn't derived from the DSL automatically. Adding a whole new resource module (a new `module:<name>` instance, not a new type) similarly means adding it to `MODULES` in the same file, plus wiring the module's Django app the way `documents/`/`projects/` do (see below).

`authz/model.py` no longer hand-builds the model with the SDK's `Userset`/`TypeDefinition` classes — it just shells out to `fga model transform` on `model.fga` and hands the resulting JSON to `WriteAuthorizationModelRequest`.

### Inspecting the model

- `docker compose exec web python manage.py show_model_graph` — prints an ASCII tree per type showing which relations imply which (following `or <relation>` and `<relation> from parent` edges), rooted at the relations nothing else feeds (e.g. `owner`, `collaborator`). It's derived straight from `model.fga` each run, so it stays accurate as the model changes.
- `docker compose exec web fga model get --store-id "$OPENFGA_STORE_ID" --api-url "$OPENFGA_API_URL" --format fga` — fetches the model actually live on the OpenFGA server (DSL form), useful to confirm it matches `model.fga` after a push.
- The OpenFGA Playground (enabled via `OPENFGA_PLAYGROUND_ENABLED=true` in `docker-compose.yml`) at `http://localhost:3000/playground` gives a visual, interactive graph plus a "check" tool, if you want more than the terminal.

## Project layout

- **`authz/`** — the shared authorization layer: the OpenFGA schema (`model.fga`), the model loader (`model.py`), the OpenFGA client wrapper (`client.py`), the `Role`/`Permission` Django models + admin + REST API, and Django signals that sync Role/Permission changes into OpenFGA tuples automatically. Also provides `OwnedObjectViewSet` / `ObjectPermission` base classes so a new resource module only needs a handful of small files.
- **`documents/`** — first resource module (title/content, owned by a user). Also demonstrates **field-level enforcement**: the `content` field is redacted in the API response unless the requester has `can_edit` on that document.
- **`projects/`** — second resource module, added to prove the pattern generalizes rather than being document-specific.
- **`config/`** — Django project settings/urls.

## Running it

```bash
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py setup_openfga   # creates the OpenFGA store + pushes the model, updates .env
docker compose restart web                                # picks up the store/model IDs written to .env
docker compose exec web python manage.py createsuperuser
```

`setup_openfga` is idempotent and safe to re-run any time the model in `authz/model.py` changes — it reuses the existing store, writes a new model version, backfills `parent` tuples for any objects created before the change, and resyncs every Role's OpenFGA tuples to the current relation names (so a relation rename doesn't leave stale tuples behind).

Services:

| Service | Purpose | Port |
|---|---|---|
| `web` | Django app | `8000` |
| `db` | App's own Postgres | `5431` (host) |
| `openfga` | OpenFGA server (HTTP / gRPC / Playground) | `8080` / `8081` / `3000` |
| `openfga-db` | OpenFGA's own Postgres | internal only |
| `openfga-migrate` | One-shot `openfga migrate`, runs then exits | — |

## API

- `POST /api/auth/login/` / `POST /api/auth/login/refresh/` — JWT login
- `GET/POST /api/documents/`, `GET/PATCH/DELETE /api/documents/{id}/`
- `GET/POST /api/projects/`, `GET/PATCH/DELETE /api/projects/{id}/`
- `GET/POST /api/roles/`, `GET/PATCH/DELETE /api/roles/{id}/`, plus `POST /api/roles/{id}/add_user/`, `remove_user/`, `add_permission/`, `remove_permission/` (staff-only)
- `GET /api/permissions/` — read-only catalog of `(module, tier)` pairs (staff-only)
- `GET /api/docs/` — Swagger UI · `GET /api/redoc/` — Redoc · `GET /api/schema/` — raw OpenAPI schema

## Notes for adopting this pattern elsewhere

- Changing the model (renaming or restructuring relations) requires an explicit resync pass over existing tuples — a tuple referencing a retired relation name doesn't error, it just goes silently inert. `setup_openfga`'s resync step is the pattern to copy.
- Pin exact Docker image versions for Postgres — a `:latest` bump mid-project can silently change the expected data directory layout.
- OpenFGA SDK errors need to be matched on the actual message text (e.g. `"already exists"` vs `"does not exist"`) to tell a harmless duplicate-write/delete-miss apart from a real validation error — there's no dedicated error code for each.
