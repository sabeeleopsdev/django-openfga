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

The model is built programmatically in [`authz/model.py`](authz/model.py) using the OpenFGA Python SDK's classes (not stored as `.fga` DSL text) and pushed to the server via `python manage.py setup_openfga`.

## Project layout

- **`authz/`** — the shared authorization layer: the OpenFGA client wrapper (`client.py`), the model builder (`model.py`), the `Role`/`Permission` Django models + admin + REST API, and Django signals that sync Role/Permission changes into OpenFGA tuples automatically. Also provides `OwnedObjectViewSet` / `ObjectPermission` base classes so a new resource module only needs a handful of small files.
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
