from rest_framework import serializers

from .models import Campaign, Donation, Pledge, Disbursement
from churches.models import Church, Pastor


class PublicCampaignSerializer(serializers.ModelSerializer):
    """Safe public representation for share links (no internal IDs exposed unnecessarily)."""
    church_name = serializers.CharField(source='church.name', read_only=True)
    pastor_name = serializers.CharField(source='pastor.full_name', read_only=True)
    progress_percent = serializers.FloatField(read_only=True)
    current_balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_raised = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Campaign
        fields = [
            'public_uuid', 'title', 'description', 'goal_amount',
            'start_date', 'end_date', 'church_name', 'pastor_name',
            'progress_percent', 'current_balance', 'total_raised', 'is_active'
        ]


class CampaignSerializer(serializers.ModelSerializer):
    progress_percent = serializers.FloatField(read_only=True)
    current_balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Campaign
        fields = '__all__'
        read_only_fields = ['public_uuid', 'created_by', 'created_at', 'updated_at']


class PledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pledge
        fields = '__all__'
        read_only_fields = ['church', 'created_at', 'updated_at']


class DonationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = '__all__'
        read_only_fields = ['church', 'status', 'received_at', 'created_at', 'updated_at', 'kesho_reference']


class InitiateDonationSerializer(serializers.Serializer):
    """Input for guest (phone-only) donation."""
    campaign_public_uuid = serializers.UUIDField()
    phone = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    donor_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    is_anonymous = serializers.BooleanField(default=False)
    # Future: recurring pledge id could be passed here


class DisbursementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disbursement
        fields = '__all__'
        read_only_fields = ['status', 'requested_at', 'approved_at', 'paid_at', 'created_at', 'updated_at']