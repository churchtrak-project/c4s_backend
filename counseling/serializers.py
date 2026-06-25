from rest_framework import serializers
from .models import Counselor, CounselingCase, CounselingSession


class CounselorSerializer(serializers.ModelSerializer):
    cases = serializers.IntegerField(source='active_cases', read_only=True)
    sessions = serializers.IntegerField(source='sessions_total', read_only=True)

    class Meta:
        model = Counselor
        fields = ['id', 'full_name', 'speciality', 'available', 'cases', 'sessions']


class CounselingCaseSerializer(serializers.ModelSerializer):
    pastor = serializers.CharField(source='pastor.full_name', read_only=True)
    counselor = serializers.CharField(source='counselor.full_name', read_only=True, default='Unassigned')
    church_name = serializers.CharField(source='church.name', read_only=True)

    class Meta:
        model = CounselingCase
        fields = ['id', 'pastor', 'counselor', 'type', 'status', 'priority', 'notes', 'church_name', 'created_at']


class CounselingSessionSerializer(serializers.ModelSerializer):
    pastor = serializers.CharField(source='case.pastor.full_name', read_only=True)
    counselor = serializers.CharField(source='case.counselor.full_name', read_only=True, default='Unassigned')

    class Meta:
        model = CounselingSession
        fields = ['id', 'pastor', 'counselor', 'date', 'time', 'type', 'format', 'status', 'topic']