import uuid

from decimal import Decimal

from django.db import models
from django.utils import timezone


class Campaign(models.Model):
    """
    A named fundraising campaign for a pastor's wellness / rest.
    This is the core of Phase 1.
    Publicly shareable via public_uuid (no login needed for donors).
    """
    church = models.ForeignKey('churches.Church', on_delete=models.CASCADE, related_name='campaigns')
    pastor = models.ForeignKey('churches.Pastor', on_delete=models.PROTECT, related_name='campaigns')

    title = models.CharField(max_length=200, help_text='e.g. "Pastor James Sabbatical Fund"')
    description = models.TextField(blank=True)
    goal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()

    # Public access token (for shareable WhatsApp/SMS links)
    public_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='created_campaigns')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.church.name})"

    @property
    def total_raised(self) -> Decimal:
        """Sum of successful donations for this campaign."""
        agg = self.donations.filter(status=Donation.STATUS_SUCCESS).aggregate(
            total=models.Sum('amount')
        )
        return agg['total'] or Decimal('0.00')

    @property
    def total_disbursed(self) -> Decimal:
        agg = self.disbursements.filter(status__in=[Disbursement.STATUS_APPROVED, Disbursement.STATUS_PAID]).aggregate(
            total=models.Sum('amount')
        )
        return agg['total'] or Decimal('0.00')

    @property
    def current_balance(self) -> Decimal:
        return self.total_raised - self.total_disbursed

    @property
    def progress_percent(self) -> float:
        if self.goal_amount <= 0:
            return 100.0
        pct = float((self.total_raised / self.goal_amount) * 100)
        return min(round(pct, 1), 100.0)


class Pledge(models.Model):
    """
    Basic recurring giving model for Phase 1.
    Donors can commit to weekly/monthly/annual support.
    Actual money still comes in as individual Donation records (via M-Pesa).
    Donations can optionally link back to a Pledge via FK.
    """
    FREQUENCY_WEEKLY = 'weekly'
    FREQUENCY_MONTHLY = 'monthly'
    FREQUENCY_ANNUAL = 'annual'
    FREQUENCY_CHOICES = [
        (FREQUENCY_WEEKLY, 'Weekly'),
        (FREQUENCY_MONTHLY, 'Monthly'),
        (FREQUENCY_ANNUAL, 'Annual'),
    ]

    STATUS_ACTIVE = 'active'
    STATUS_PAUSED = 'paused'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_PAUSED, 'Paused'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    church = models.ForeignKey('churches.Church', on_delete=models.CASCADE, related_name='pledges')
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='pledges', null=True, blank=True)

    donor_phone = models.CharField(max_length=20, db_index=True)
    donor_name = models.CharField(max_length=150, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default=FREQUENCY_MONTHLY)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    start_date = models.DateField(default=timezone.now)
    next_due_date = models.DateField(null=True, blank=True, help_text="When to expect next contribution")

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Pledge {self.donor_phone} - {self.amount} {self.frequency} for {self.campaign or self.church}"


class Donation(models.Model):
    """
    Incoming contribution (primarily guest M-Pesa via KeshoPay).
    Purely phone-based, no account required.
    Can be linked to a recurring Pledge.
    """
    STATUS_PENDING = 'pending'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCESS, 'Successful'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    church = models.ForeignKey('churches.Church', on_delete=models.CASCADE, related_name='donations')
    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT, related_name='donations')

    # Optional link to recurring commitment
    pledge = models.ForeignKey(Pledge, on_delete=models.SET_NULL, null=True, blank=True, related_name='donations')

    donor_phone = models.CharField(max_length=20, db_index=True)
    donor_name = models.CharField(max_length=150, blank=True)
    is_anonymous = models.BooleanField(default=False)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    kesho_reference = models.CharField(max_length=100, blank=True, db_index=True, help_text="Our reference sent to KeshoPay")
    provider_transaction_id = models.CharField(max_length=100, blank=True, db_index=True, help_text="KeshoPay transactionId")

    received_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['church', 'status']),
            models.Index(fields=['campaign', 'status']),
        ]

    def __str__(self):
        anon = " (anonymous)" if self.is_anonymous else ""
        return f"{self.amount} {self.currency} from {self.donor_phone}{anon} → {self.campaign.title}"


class Disbursement(models.Model):
    """
    Money leaving the Pastoral Wellness Fund for approved pastor rest/wellness activities.
    Requires multi-level approval (initiate by ChurchAdmin, approve by Finance/ Accountability).
    Payout target is a specific M-Pesa number (pastor or vendor).
    """
    STATUS_REQUESTED = 'requested'
    STATUS_APPROVED = 'approved'
    STATUS_PAID = 'paid'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_REQUESTED, 'Requested'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_PAID, 'Paid'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    church = models.ForeignKey('churches.Church', on_delete=models.CASCADE, related_name='disbursements')
    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT, related_name='disbursements')

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.TextField(help_text="e.g. 'The Sabbath Week retreat for Pastor James at Lake Naivasha'")

    # Multi-level approval
    requested_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='requested_disbursements')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_disbursements')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_REQUESTED, db_index=True)

    # Payout details (directly to M-Pesa as per requirements)
    payout_phone = models.CharField(max_length=20, help_text="M-Pesa number that will receive the funds")
    payout_reference = models.CharField(max_length=100, blank=True, help_text="KeshoPay or manual payout ref")

    # Accountability / proof (no complex upload UI required yet; uses MEDIA_ROOT)
    proof_notes = models.TextField(blank=True, help_text="Description of what the funds were used for + any reference numbers")
    proof_file = models.FileField(upload_to='disbursement_proofs/', blank=True, null=True,
                                   help_text="Optional receipt, invoice, booking confirmation etc. Stored on server MEDIA_ROOT")

    requested_at = models.DateTimeField(default=timezone.now)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Disburse {self.amount} for {self.campaign.title} ({self.get_status_display()})"
