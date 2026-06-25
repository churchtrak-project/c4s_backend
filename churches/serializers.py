from rest_framework import serializers

from .models import Church, Pastor, Member, ChurchEvent, Task, ContentResource, WellnessAssessment
from accounts.models import User


class PastorMiniSerializer(serializers.ModelSerializer):
    """Light pastor info for church lists."""
    name = serializers.CharField(source='full_name')

    class Meta:
        model = Pastor
        fields = ['id', 'name']


class ChurchSerializer(serializers.ModelSerializer):
    """Full + list representation for CFS admin churches page and scoped views."""
    pastor = serializers.SerializerMethodField()
    members = serializers.IntegerField(source='member_count', read_only=True)
    wellness = serializers.IntegerField(source='wellness_avg', read_only=True)
    fund = serializers.DecimalField(source='current_fund_balance', max_digits=12, decimal_places=2, read_only=True)
    status = serializers.SerializerMethodField()
    joined = serializers.SerializerMethodField()

    class Meta:
        model = Church
        fields = [
            'id', 'name', 'county', 'pastor', 'members', 'plan', 'status',
            'wellness', 'fund', 'joined', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_pastor(self, obj):
        p = getattr(obj, 'pastor', None)
        if p:
            return p.full_name
        # fallback: first user with pastor role in church
        pastor_user = obj.users.filter(role=User.ROLE_PASTOR).first()
        return pastor_user.full_name if pastor_user else '—'

    def get_status(self, obj):
        return 'Active' if obj.is_active else 'Onboarding'

    def get_joined(self, obj):
        return obj.created_at.strftime('%b %Y') if obj.created_at else ''


class PastorSerializer(serializers.ModelSerializer):
    """Detailed pastor for CFS pastors page + scoped."""
    name = serializers.SerializerMethodField()
    church = serializers.CharField(source='church.name', read_only=True)
    years = serializers.IntegerField(source='years_of_service', read_only=True)
    wellness = serializers.IntegerField(source='wellness_score', read_only=True)
    lastRest = serializers.SerializerMethodField()
    counselor = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)
    assessmentDue = serializers.BooleanField(source='assessment_due', read_only=True)

    class Meta:
        model = Pastor
        fields = [
            'id', 'name', 'church', 'years', 'wellness', 'lastRest',
            'counselor', 'status', 'assessmentDue', 'full_name', 'phone', 'email'
        ]

    def get_name(self, obj):
        return obj.full_name

    def get_lastRest(self, obj):
        return obj.last_rest_display

    def get_counselor(self, obj):
        return obj.counselor_display


class ChurchDetailSerializer(ChurchSerializer):
    """Slightly richer for detail views."""
    class Meta(ChurchSerializer.Meta):
        fields = ChurchSerializer.Meta.fields + ['contact_phone', 'contact_email', 'notes']


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['id', 'full_name', 'phone', 'county', 'cell_group', 'ministry', 'attendance', 'baptized', 'status', 'joined', 'email']


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChurchEvent
        fields = ['id', 'title', 'type', 'format', 'date', 'location', 'capacity', 'registered', 'fee', 'status', 'is_cfs_event']


class TaskSerializer(serializers.ModelSerializer):
    assignedTo = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'assignedTo', 'assignee_name', 'due_date', 'priority', 'status', 'done']

    def get_assignedTo(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.full_name or str(obj.assigned_to)
        return obj.assignee_name or '—'


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentResource
        fields = ['id', 'title', 'author', 'type', 'category', 'audience', 'views', 'status', 'date', 'is_cfs']


class WellnessAssessmentSerializer(serializers.ModelSerializer):
    pastor_name = serializers.CharField(source='pastor.full_name', read_only=True)

    class Meta:
        model = WellnessAssessment
        fields = ['id', 'pastor_name', 'assessment_date', 'overall_score', 'dimension_scores', 'answers', 'notes']