from datetime import date

from rest_framework import serializers

from .models import Campaign, CampaignUpdate, Donation, Pledge, Disbursement


def _pastor_initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else 'PK'


class CampaignUpdateSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()

    class Meta:
        model = CampaignUpdate
        fields = ['id', 'date', 'author_name', 'text', 'created_at']
        read_only_fields = ['id', 'created_at', 'author_name']

    def get_date(self, obj):
        return obj.created_at.strftime('%b %d')


class PublicDonorSerializer(serializers.Serializer):
    name = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    time = serializers.CharField()
    anonymous = serializers.BooleanField()


class PublicLedgerEntrySerializer(serializers.Serializer):
    date = serializers.CharField()
    desc = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    type = serializers.CharField()
    approved = serializers.BooleanField()
    proof = serializers.BooleanField()


class PublicCampaignSerializer(serializers.ModelSerializer):
    church = serializers.CharField(source='church.name', read_only=True)
    pastor = serializers.CharField(source='pastor.full_name', read_only=True)
    initials = serializers.SerializerMethodField()
    story = serializers.CharField(source='description', read_only=True)
    raised = serializers.DecimalField(source='total_raised', max_digits=12, decimal_places=2, read_only=True)
    goal = serializers.DecimalField(source='goal_amount', max_digits=12, decimal_places=2, read_only=True)
    donors = serializers.IntegerField(source='donor_count', read_only=True)
    daysLeft = serializers.IntegerField(source='days_left', read_only=True)
    progress_percent = serializers.FloatField(read_only=True)
    current_balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_raised = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    updates = serializers.SerializerMethodField()
    donors_list = serializers.SerializerMethodField()
    ledger = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'public_uuid', 'title', 'story', 'goal', 'raised', 'donors', 'daysLeft',
            'church', 'pastor', 'initials', 'progress_percent', 'current_balance',
            'total_raised', 'is_active', 'start_date', 'end_date',
            'updates', 'donors_list', 'ledger',
        ]

    def get_initials(self, obj):
        return _pastor_initials(obj.pastor.full_name)

    def get_updates(self, obj):
        qs = obj.updates.all()[:10]
        return CampaignUpdateSerializer(qs, many=True).data

    def get_donors_list(self, obj):
        from django.utils import timezone
        donations = (
            obj.donations.filter(status=Donation.STATUS_SUCCESS)
            .order_by('-received_at')[:20]
        )
        out = []
        for d in donations:
            when = d.received_at or d.created_at
            delta = timezone.now() - when
            if delta.days:
                time_label = f"{delta.days}d ago"
            else:
                hours = max(int(delta.total_seconds() // 3600), 1)
                time_label = f"{hours}h ago"
            out.append({
                'name': 'Anonymous' if d.is_anonymous else (d.donor_name or d.donor_phone),
                'amount': d.amount,
                'time': time_label,
                'anonymous': d.is_anonymous,
            })
        return out

    def get_ledger(self, obj):
        entries = []
        for d in obj.disbursements.filter(
            status__in=[Disbursement.STATUS_APPROVED, Disbursement.STATUS_PAID]
        ).order_by('-approved_at')[:15]:
            when = d.approved_at or d.requested_at
            entries.append({
                'date': when.strftime('%b %d') if when else '',
                'desc': d.purpose[:120],
                'amount': d.amount,
                'type': 'Disbursement',
                'approved': True,
                'proof': bool(d.proof_file or d.proof_notes),
            })
        return entries


class CampaignSerializer(serializers.ModelSerializer):
    raised = serializers.DecimalField(source='total_raised', max_digits=12, decimal_places=2, read_only=True)
    goal = serializers.DecimalField(source='goal_amount', max_digits=12, decimal_places=2, read_only=True)
    donors = serializers.IntegerField(source='donor_count', read_only=True)
    daysLeft = serializers.IntegerField(source='days_left', read_only=True)
    status = serializers.CharField(source='status_label', read_only=True)
    pastor = serializers.CharField(source='pastor.full_name', read_only=True)
    pastor_id = serializers.PrimaryKeyRelatedField(
        queryset=Campaign.pastor.field.related_model.objects.all(),
        source='pastor',
        write_only=True,
        required=False,
    )
    progress_percent = serializers.FloatField(read_only=True)
    current_balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    created = serializers.SerializerMethodField()
    ends = serializers.SerializerMethodField()
    share_url = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'public_uuid', 'title', 'description', 'goal_amount', 'goal',
            'raised', 'donors', 'daysLeft', 'status', 'pastor', 'pastor_id',
            'start_date', 'end_date', 'created', 'ends', 'share_url',
            'progress_percent', 'current_balance', 'is_active', 'church',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'public_uuid', 'created_by', 'created_at', 'updated_at', 'church',
        ]

    def get_created(self, obj):
        return obj.start_date.strftime('%b %d, %Y')

    def get_ends(self, obj):
        return obj.end_date.strftime('%b %d, %Y')

    def get_share_url(self, obj):
        return f'/public-campaign?uuid={obj.public_uuid}'


class CampaignCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = ['title', 'description', 'goal_amount', 'start_date', 'end_date', 'pastor', 'is_active']


class PledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pledge
        fields = '__all__'
        read_only_fields = ['church', 'created_at', 'updated_at']


class DonationSerializer(serializers.ModelSerializer):
    ref = serializers.CharField(source='kesho_reference', read_only=True)
    donor = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    method = serializers.CharField(source='payment_method', read_only=True)
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)
    anonymous = serializers.BooleanField(source='is_anonymous', read_only=True)
    receiptSent = serializers.BooleanField(source='receipt_sent', read_only=True)
    phone = serializers.CharField(source='donor_phone', read_only=True)

    class Meta:
        model = Donation
        fields = [
            'id', 'ref', 'donor', 'phone', 'amount', 'date', 'time', 'method',
            'campaign_title', 'anonymous', 'receiptSent', 'status', 'received_at',
            'created_at',
        ]
        read_only_fields = fields

    def get_donor(self, obj):
        if obj.is_anonymous:
            return 'Anonymous'
        return obj.donor_name or obj.donor_phone

    def get_date(self, obj):
        when = obj.received_at or obj.created_at
        return when.strftime('%b %d, %Y') if when else ''

    def get_time(self, obj):
        when = obj.received_at or obj.created_at
        return when.strftime('%H:%M') if when else ''


class InitiateDonationSerializer(serializers.Serializer):
    campaign_public_uuid = serializers.UUIDField()
    phone = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    donor_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    is_anonymous = serializers.BooleanField(default=False)
    recurring = serializers.ChoiceField(
        choices=['once', 'weekly', 'monthly'],
        default='once',
        required=False,
    )


class DisbursementSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)
    requestedBy = serializers.SerializerMethodField()
    requestDate = serializers.SerializerMethodField()
    intendedDate = serializers.SerializerMethodField()
    ref = serializers.CharField(source='reference', read_only=True)
    status_label = serializers.CharField(source='status_display_frontend', read_only=True)
    sigs = serializers.IntegerField(source='signature_count', read_only=True)
    proof = serializers.SerializerMethodField()
    signatures = serializers.SerializerMethodField()

    class Meta:
        model = Disbursement
        fields = [
            'id', 'ref', 'purpose', 'amount', 'category', 'campaign', 'campaign_title',
            'status', 'status_label', 'requestedBy', 'requestDate', 'intendedDate',
            'sigs', 'proof', 'signatures', 'notes', 'proof_notes', 'proof_file',
            'payout_phone', 'requested_at', 'approved_at', 'paid_at',
        ]
        read_only_fields = [
            'status', 'reference', 'requested_by', 'approved_by', 'rejected_by',
            'requested_at', 'approved_at', 'paid_at', 'created_at', 'updated_at',
        ]

    def get_requestedBy(self, obj):
        return obj.requested_by.full_name or obj.requested_by.email or obj.requested_by.phone

    def get_requestDate(self, obj):
        return obj.requested_at.strftime('%b %d, %Y') if obj.requested_at else ''

    def get_intendedDate(self, obj):
        if obj.intended_date:
            return obj.intended_date.strftime('%b %d, %Y')
        return ''

    def get_proof(self, obj):
        return bool(obj.proof_file or obj.proof_notes)

    def get_signatures(self, obj):
        return obj.signatures_payload()


class DisbursementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disbursement
        fields = [
            'campaign', 'amount', 'purpose', 'category', 'intended_date',
            'payout_phone', 'notes', 'proof_notes', 'proof_file',
        ]

    def validate_campaign(self, campaign):
        user = self.context['request'].user
        if not user.is_cfs_user and user.church_id != campaign.church_id:
            raise serializers.ValidationError('Campaign not in your church.')
        return campaign


class DisbursementRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class ResendReceiptSerializer(serializers.Serializer):
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=['sms', 'email']),
        required=False,
        default=['sms', 'email'],
    )