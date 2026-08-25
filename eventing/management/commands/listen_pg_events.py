import json
import select

import inngest
import psycopg2
import psycopg2.extensions
from django.conf import settings
from django.core.management.base import BaseCommand

from eventing.client import inngest_client
from eventing.functions import DB_CHANGE_EVENT

POLL_TIMEOUT_SECONDS = 5


class Command(BaseCommand):
    help = (
        "LISTEN on the Postgres NOTIFY channel populated by the eventing "
        "triggers, and forward each notification to Inngest as an event. "
        "Runs its own connection outside Django's ORM pool since LISTEN "
        "needs a long-lived, autocommit connection."
    )

    def handle(self, *_args, **_options):
        conn = self._connect()
        channel = settings.PG_NOTIFY_CHANNEL

        with conn.cursor() as cur:
            cur.execute(f"LISTEN {channel};")

        self.stdout.write(
            self.style.SUCCESS(f"Listening on Postgres channel '{channel}'...")
        )

        try:
            while True:
                if not select.select([conn], [], [], POLL_TIMEOUT_SECONDS)[0]:
                    continue
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    self._forward(notify)
        except KeyboardInterrupt:
            self.stdout.write("Stopping listener.")
        finally:
            conn.close()

    def _connect(self):
        db = settings.DATABASES["default"]
        conn = psycopg2.connect(
            dbname=db["NAME"],
            user=db["USER"],
            password=db["PASSWORD"],
            host=db["HOST"],
            port=db["PORT"],
        )
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        return conn

    def _forward(self, notify):
        try:
            payload = json.loads(notify.payload)
        except ValueError:
            self.stderr.write(f"Ignoring non-JSON payload: {notify.payload!r}")
            return

        table = payload.get("table", "unknown")
        op = payload.get("op", "UNKNOWN")

        ids = inngest_client.send_sync(
            inngest.Event(name=DB_CHANGE_EVENT, data=payload)
        )

        self.stdout.write(
            f"{table}.{op} -> sent {DB_CHANGE_EVENT} (inngest event id: {ids[0]})"
        )
