from django.db import models
from django.utils import timezone


class PaymentTransaction(models.Model):
    """
    Full audit log of every interaction with KeshoPay (and future providers).
    Stores raw responses for debugging and compliance.
    One merchant account on KeshoPay side — church/campaign attribution via reference + metadata.
    """
    DIRECTION_IN = 'in'
    DIRECTION_OUT = 'out'
    DIRECTION_CHOICES = [
        (DIRECTION_IN, 'Incoming (Donation)'),
        (DIRECTION_OUT, 'Outgoing (Disbursement/Payout)'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'

    church = models.ForeignKey('churches.Church', on_delete=models.CASCADE, related_name='payment_transactions')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')

    # Our side
    reference = models.CharField(max_length=120, db_index=True, help_text="Internal reference we sent (e.g. CAMP-uuid or DISB-xxx)")
    related_donation = models.ForeignKey('fundraising.Donation', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    related_disbursement = models.ForeignKey('fundraising.Disbursement', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')

    # KeshoPay side
    provider = models.CharField(max_length=30, default='keshopay')
    provider_reference = models.CharField(max_length=120, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=[
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
    ], default=STATUS_PENDING, db_index=True)

    phone_number = models.CharField(max_length=20, blank=True)

    raw_request = models.JSONField(default=dict, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    webhook_payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['church', 'status']),
            models.Index(fields=['provider_reference']),
        ]

    def __str__(self):
        return f"{self.provider} {self.direction} {self.amount} ({self.status}) ref={self.reference}"
