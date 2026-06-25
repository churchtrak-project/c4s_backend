from rest_framework import serializers

from churches.models import Church, Pastor
from .models import User


class UserProfileSerializer(serializers.ModelSerializer):
    """Shape returned to frontend for logged-in user (matches lib/types.ts User + demo needs)."""
    name = serializers.SerializerMethodField()
    church = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'role', 'church', 'initials']

    def get_name(self, obj):
        return obj.full_name or obj.email or obj.phone

    def get_church(self, obj):
        return obj.church.name if obj.church else None

    def get_initials(self, obj):
        name = obj.full_name or ''
        parts = [p for p in name.split() if p]
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        if name:
            return name[:2].upper()
        if obj.email:
            return obj.email[:2].upper()
        return obj.phone[-2:] if obj.phone else 'U'


class LoginSerializer(serializers.Serializer):
    """Accept email or phone + password (supports frontend DEMO_USERS style emails)."""
    identifier = serializers.CharField(help_text="Email or phone number")
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate
        identifier = attrs.get('identifier', '').strip().lower()
        password = attrs.get('password')

        user = None
        # Try email first (for demo accounts)
        if '@' in identifier:
            try:
                user_obj = User.objects.get(email__iexact=identifier)
                user = authenticate(phone=user_obj.phone, password=password)
            except User.DoesNotExist:
                pass
        if not user:
            # Try phone (normalize)
            norm_phone = User.objects.normalize_phone(identifier) if hasattr(User.objects, 'normalize_phone') else identifier
            user = authenticate(phone=norm_phone, password=password)
        if not user:
            # Last attempt: direct phone lookup + check
            try:
                candidate = User.objects.get(phone=identifier) if not '@' in identifier else None
                if candidate and candidate.check_password(password):
                    user = candidate
            except User.DoesNotExist:
                pass

        if not user:
            raise serializers.ValidationError("Invalid credentials. Check email/phone and password.")
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive.")

        attrs['user'] = user
        return attrs


class ChurchSignupSerializer(serializers.Serializer):
    """
    Public self-signup for a new church (Phase 1).
    Creates:
      - Church
      - Initial ChurchAdmin User (with password)
      - Primary Pastor record
      - (Optional) a starter Campaign
    """
    # Church
    church_name = serializers.CharField(max_length=200)
    county = serializers.CharField(max_length=100, required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)

    # Initial Church Admin who will manage the church
    admin_phone = serializers.CharField(max_length=20)
    admin_full_name = serializers.CharField(max_length=150)
    admin_password = serializers.CharField(write_only=True, min_length=8)

    # Primary Pastor (one per church)
    pastor_full_name = serializers.CharField(max_length=150)
    pastor_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    # Optional starter campaign
    create_starter_campaign = serializers.BooleanField(default=True)
    starter_campaign_title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    starter_goal = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)

    def validate_admin_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("A user with this phone already exists.")
        return value

    def create(self, validated_data):
        from django.db import transaction
        from django.utils.text import slugify
        import uuid

        with transaction.atomic():
            # 1. Create Church
            church = Church.objects.create(
                name=validated_data['church_name'],
                slug=slugify(validated_data['church_name']) + '-' + str(uuid.uuid4())[:8],
                county=validated_data.get('county', ''),
                contact_phone=validated_data.get('contact_phone', ''),
                contact_email=validated_data.get('contact_email', ''),
            )

            # 2. Create Church Admin user
            admin_user = User.objects.create_user(
                phone=validated_data['admin_phone'],
                password=validated_data['admin_password'],
                full_name=validated_data['admin_full_name'],
                role=User.ROLE_CHURCH_ADMIN,
                church=church,
            )

            # 3. Create Pastor
            pastor = Pastor.objects.create(
                church=church,
                full_name=validated_data['pastor_full_name'],
                phone=validated_data.get('pastor_phone', ''),
            )

            # 4. Optional starter campaign
            if validated_data.get('create_starter_campaign'):
                from fundraising.models import Campaign
                from datetime import date, timedelta

                title = validated_data.get('starter_campaign_title') or f"Pastoral Wellness Fund for {pastor.full_name}"
                goal = validated_data.get('starter_goal') or 50000

                Campaign.objects.create(
                    church=church,
                    pastor=pastor,
                    title=title,
                    goal_amount=goal,
                    start_date=date.today(),
                    end_date=date.today() + timedelta(days=90),
                    created_by=admin_user,
                )

            return {
                'church': church,
                'admin_user': admin_user,
                'pastor': pastor,
            }