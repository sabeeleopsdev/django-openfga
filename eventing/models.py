from django.db import models


class EventLog(models.Model):
    """Record of a pg_notify payload that was forwarded to Inngest.

    Exists purely to make the demo observable in /admin - not a queue,
    not a source of truth.
    """

    table = models.CharField(max_length=100)
    operation = models.CharField(max_length=10)
    event_name = models.CharField(max_length=255)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "processed" if self.processed else "pending"
        return f"{self.event_name} ({status})"
