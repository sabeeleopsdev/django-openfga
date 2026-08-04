from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_by")
    search_fields = ("title", "created_by__username")
    list_filter = ("created_by",)
