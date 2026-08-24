import json
import subprocess

from django.core.management.base import BaseCommand

from authz.model import MODEL_FILE


def _describe_type_ref(ref):
    if ref.get("relation"):
        return f"{ref['type']}#{ref['relation']}"
    return ref["type"]


def _walk(userset, implied_by, from_parent, has_direct_grant):
    """Recurses through a relation's userset expression, filling in:
    - implied_by: relation names whose truth also makes this relation true
      (i.e. a `computedUserset` child - "or <relation>" in the DSL)
    - from_parent: relation names inherited via `<relation> from parent`
    - has_direct_grant: set to True if the relation allows direct tuples (`this`)
    """
    if "this" in userset:
        has_direct_grant.add(True)
    elif "computedUserset" in userset:
        implied_by.append(userset["computedUserset"]["relation"])
    elif "tupleToUserset" in userset:
        from_parent.append(userset["tupleToUserset"]["computedUserset"]["relation"])
    else:
        for key, extract in (
            ("union", lambda u: u["child"]),
            ("intersection", lambda u: u["child"]),
            ("difference", lambda u: [u["base"], u["subtract"]]),
        ):
            if key in userset:
                for child in extract(userset[key]):
                    _walk(child, implied_by, from_parent, has_direct_grant)
                return


class Command(BaseCommand):
    help = "Prints an ASCII dependency graph of authz/model.fga: which relations imply which."

    def handle(self, *args, **options):
        try:
            result = subprocess.run(
                ["fga", "model", "transform", "--file", str(MODEL_FILE), "--output-format", "json"],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            self.stderr.write(exc.stderr)
            raise SystemExit(1)

        model = json.loads(result.stdout)

        for type_def in model["type_definitions"]:
            type_name = type_def["type"]
            relations = type_def.get("relations", {})
            if not relations:
                continue

            metadata_relations = (type_def.get("metadata") or {}).get("relations", {})
            info = {}
            for relation, userset in relations.items():
                implied_by, from_parent, has_direct_grant = [], [], set()
                _walk(userset, implied_by, from_parent, has_direct_grant)
                info[relation] = {
                    "implied_by": implied_by,
                    "from_parent": from_parent,
                    "direct": bool(has_direct_grant),
                }

            # "implies" is the reverse of "implied_by": X -> {relations X unlocks}
            implies = {relation: [] for relation in relations}
            for relation, data in info.items():
                for source in data["implied_by"]:
                    implies[source].append(relation)

            # Roots are relations nothing else feeds into via `or <relation>` -
            # only direct grants and/or parent inheritance, e.g. owner, collaborator.
            roots = [r for r in relations if not info[r]["implied_by"]]

            self.stdout.write(self.style.MIGRATE_LABEL(f"\n{type_name}"))

            def render(relation, depth):
                data = info[relation]
                tags = []
                if data["direct"]:
                    types = ", ".join(
                        _describe_type_ref(t)
                        for t in metadata_relations.get(relation, {}).get("directly_related_user_types", [])
                    )
                    tags.append(f"direct: [{types}]")
                for parent_relation in data["from_parent"]:
                    tags.append(f"inherits {parent_relation} from parent")
                suffix = f"  ({'; '.join(tags)})" if tags else ""
                indent = "  " + "    " * depth
                bullet = "└─ " if depth else ""
                self.stdout.write(f"{indent}{bullet}{relation}{suffix}")
                for target in sorted(implies[relation]):
                    render(target, depth + 1)

            for relation in roots:
                render(relation, 0)
