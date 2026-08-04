from django.contrib import admin

from .models import Document

# Register your models here.
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_by")
    search_fields = ("title", "created_by__username")
    list_filter = ("created_by",)
    ordering = ("title",)

admin.site.register(Document, DocumentAdmin)