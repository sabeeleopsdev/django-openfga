from django.contrib import admin

from .models import Permission, Role



@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('id', "module", "relation")
    list_filter = ("module", "relation")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', "name", "description")
    filter_horizontal = ("permissions", "users")