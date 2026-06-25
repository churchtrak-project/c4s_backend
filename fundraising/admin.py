from django.contrib import admin
from django.utils.html import format_html

from .models import Campaign, Pledge, Donation, Disbursement


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'church', 'pastor', 'goal_amount', 'progress', 'is_active', 'end_date')
    list_filter = ('is_active', 'church')
    search_fields = ('title', 'church__name', 'pastor__full_name')
    autocomplete_fields = ['church', 'pastor', 'created_by']
    readonly_fields = ('public_uuid', 'created_at', 'updated_at', 'progress_display')

    def progress(self, obj):
        return f"{obj.progress_percent}%"

    def progress_display(self, obj):
        return format_html(
            '<strong>{}%</strong> raised of {} (Balance: {})',
            obj.progress_percent, obj.goal_amount, obj.current_balance
        )
    progress_display.short_description = 'Progress & Balance'


@admin.register(Pledge)
class PledgeAdmin(admin.ModelAdmin):
    list_display = ('donor_phone', 'amount', 'frequency', 'status', 'campaign', 'next_due_date')
    list_filter = ('status', 'frequency', 'church')
    search_fields = ('donor_phone', 'donor_name')
    autocomplete_fields = ['church', 'campaign']


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('amount', 'currency', 'donor_phone', 'status', 'campaign', 'is_anonymous', 'received_at')
    list_filter = ('status', 'is_anonymous', 'church')
    search_fields = ('donor_phone', 'donor_name', 'kesho_reference', 'provider_transaction_id')
    autocomplete_fields = ['church', 'campaign', 'pledge']
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Disbursement)
class DisbursementAdmin(admin.ModelAdmin):
    list_display = ('amount', 'campaign', 'status', 'requested_by', 'approved_by', 'payout_phone')
    list_filter = ('status', 'church')
    search_fields = ('purpose', 'payout_phone', 'payout_reference')
    autocomplete_fields = ['church', 'campaign', 'requested_by', 'approved_by']
    readonly_fields = ('requested_at', 'created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('church', 'campaign', 'amount', 'purpose', 'payout_phone')
        }),
        ('Approval Workflow', {
            'fields': ('status', 'requested_by', 'approved_by', 'requested_at', 'approved_at', 'paid_at')
        }),
        ('Accountability & Proof (MEDIA_ROOT)', {
            'fields': ('proof_notes', 'proof_file', 'payout_reference', 'notes')
        }),
    )
