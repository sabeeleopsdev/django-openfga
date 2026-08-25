from django.db import migrations

# Fires PERFORM pg_notify(<channel>, <json payload>) on row changes. Payload
# shape: {"table": TG_TABLE_NAME, "op": TG_OP, "id": <pk>, "data": <row>}.
# The channel name is baked in here (rather than read from settings.py, which
# SQL can't see) and must match PG_NOTIFY_CHANNEL / settings.PG_NOTIFY_CHANNEL.
CHANNEL = "eventing_channel"

CREATE_FUNCTION_SQL = f"""
CREATE OR REPLACE FUNCTION eventing_notify() RETURNS trigger AS $$
DECLARE
    row_data json;
BEGIN
    row_data := row_to_json(COALESCE(NEW, OLD));
    PERFORM pg_notify(
        '{CHANNEL}',
        json_build_object(
            'table', TG_TABLE_NAME,
            'op', TG_OP,
            'id', (row_data ->> 'id'),
            'data', row_data
        )::text
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
"""

DROP_FUNCTION_SQL = "DROP FUNCTION IF EXISTS eventing_notify() CASCADE;"

WATCHED_TABLES = ["documents_document", "projects_project"]


def _create_trigger_sql(table: str) -> str:
    return f"""
    DROP TRIGGER IF EXISTS {table}_notify ON {table};
    CREATE TRIGGER {table}_notify
    AFTER INSERT OR UPDATE OR DELETE ON {table}
    FOR EACH ROW EXECUTE FUNCTION eventing_notify();
    """


def _drop_trigger_sql(table: str) -> str:
    return f"DROP TRIGGER IF EXISTS {table}_notify ON {table};"


class Migration(migrations.Migration):

    dependencies = [
        ("eventing", "0001_initial"),
        ("documents", "0001_initial"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_FUNCTION_SQL,
            reverse_sql=DROP_FUNCTION_SQL,
        ),
        *[
            migrations.RunSQL(
                sql=_create_trigger_sql(table),
                reverse_sql=_drop_trigger_sql(table),
            )
            for table in WATCHED_TABLES
        ],
    ]
