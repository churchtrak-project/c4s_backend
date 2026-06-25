from django.contrib import admin

from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('provider', 'direction', 'amount', 'status', 'reference', 'provider_reference', 'church', 'created_at')
    list_filter = ('provider', 'direction', 'status', 'church')
    search_fields = ('reference', 'provider_reference', 'phone_number')
    readonly_fields = ('raw_request', 'raw_response', 'webhook_payload', 'created_at', 'updated_at')
    autocomplete_fields = ['church', 'related_donation', 'related_disbursement']
