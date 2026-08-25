from django.contrib import admin

from eventing.models import EventLog


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ("event_name", "table", "operation", "processed", "created_at")
    list_filter = ("table", "operation", "processed")
    readonly_fields = ("table", "operation", "event_name", "payload", "created_at")
