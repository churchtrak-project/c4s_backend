from django.contrib import admin

from .models import Church, Pastor


@admin.register(Church)
class ChurchAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'county', 'is_active', 'created_at')
    list_filter = ('is_active', 'county')
    search_fields = ('name', 'slug', 'contact_phone')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Pastor)
class PastorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'church', 'phone', 'last_rest_date', 'total_retreats_taken')
    search_fields = ('full_name', 'phone', 'church__name')
    autocomplete_fields = ['church', 'user']
    readonly_fields = ('created_at', 'updated_at')
