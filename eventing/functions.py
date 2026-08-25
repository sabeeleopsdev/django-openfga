import inngest
from django.conf import settings
from django.core.mail import send_mail

from eventing.client import inngest_client
from eventing.models import EventLog

# Emitted by the pg_notify listener (see
# eventing/management/commands/listen_pg_events.py) for every watched table.
# Table/operation travel in event.data rather than the event name, so one
# function handles all of them - and none of this touches FGA/authz.
DB_CHANGE_EVENT = "db/record.changed"


@inngest_client.create_function(
    fn_id="handle-db-change",
    trigger=inngest.TriggerEvent(event=DB_CHANGE_EVENT),
    retries=3,
)
def handle_db_change(ctx: inngest.ContextSync) -> dict:
    event = ctx.event

    def _log_event() -> int:
        entry = EventLog.objects.create(
            table=event.data.get("table", "unknown"),
            operation=event.data.get("op", "UNKNOWN"),
            event_name=event.name,
            payload=event.data,
        )
        return entry.id

    log_id = ctx.step.run("log-event", _log_event)

    def _send_notification_email() -> bool:
        if not settings.EVENTING_NOTIFY_EMAIL:
            return False
        table = event.data.get("table", "unknown")
        op = event.data.get("op", "UNKNOWN")
        record_id = event.data.get("id")
        sent = send_mail(
            subject=f"[eventing] {table} {op} (id={record_id})",
            message=(
                f"Table: {table}\nOperation: {op}\nRecord ID: {record_id}\n\n"
                f"Row data: {event.data.get('data')}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.EVENTING_NOTIFY_EMAIL],
        )
        return sent > 0

    ctx.step.run("send-notification-email", _send_notification_email)

    def _mark_processed() -> None:
        EventLog.objects.filter(id=log_id).update(processed=True)

    ctx.step.run("mark-processed", _mark_processed)

    return {"log_id": log_id, "event": event.name}
