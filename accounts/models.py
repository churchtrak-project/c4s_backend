import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom manager so phone can be the main identifier (Kenya-friendly)."""

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Users must have a phone number')
        phone = self.normalize_phone(phone)
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.ROLE_CFS_ADMIN)
        return self.create_user(phone, password, **extra_fields)

    @staticmethod
    def normalize_phone(phone):
        phone = phone.strip().replace(' ', '').replace('-', '')
        if phone.startswith('0') and len(phone) == 10:
            phone = '+254' + phone[1:]
        elif phone.startswith('254') and not phone.startswith('+'):
            phone = '+' + phone
        return phone


class User(AbstractUser):
    """
    Custom user for the platform.
    - CFS staff use this globally (church is null)
    - Church users have church FK + role
    Phone is the primary login identifier for simplicity in Kenyan context.
    """

    # Align with frontend UserRole for full platform support (email/demo friendly names kept where possible)
    ROLE_CFS_SUPERADMIN = 'cfs_superadmin'
    ROLE_CFS_ADMIN = 'cfs_admin'
    ROLE_CFS_STAFF = 'cfs_staff'
    ROLE_CHURCH_ADMIN = 'church_admin'
    ROLE_FINANCE_OFFICER = 'finance_officer'
    ROLE_PASTOR = 'pastor'
    ROLE_MINISTRY_LEADER = 'ministry_leader'
    ROLE_COUNSELOR = 'counselor'
    ROLE_CHURCH_MEMBER = 'church_member'
    ROLE_DONOR = 'donor'

    ROLE_CHOICES = [
        (ROLE_CFS_SUPERADMIN, 'CFS Super Admin'),
        (ROLE_CFS_ADMIN, 'CFS Super Admin'),
        (ROLE_CFS_STAFF, 'CFS Staff'),
        (ROLE_CHURCH_ADMIN, 'Church Admin'),
        (ROLE_FINANCE_OFFICER, 'Finance Officer'),
        (ROLE_PASTOR, 'Pastor'),
        (ROLE_MINISTRY_LEADER, 'Ministry Leader'),
        (ROLE_COUNSELOR, 'Counselor'),
        (ROLE_CHURCH_MEMBER, 'Church Member'),
        (ROLE_DONOR, 'Donor / Partner'),
    ]

    # Remove username requirement - use phone
    username = None
    phone = models.CharField(max_length=20, unique=True, db_index=True)
    email = models.EmailField(blank=True, null=True)

    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default=ROLE_CHURCH_MEMBER)
    church = models.ForeignKey(
        'churches.Church',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
        help_text="Null for global CFS users. Required for church-scoped roles."
    )

    # Track basic profile
    full_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['role']   # email optional

    objects = UserManager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.phone} ({self.get_role_display()})"

    @property
    def is_cfs_user(self):
        return self.role in (self.ROLE_CFS_SUPERADMIN, self.ROLE_CFS_ADMIN, self.ROLE_CFS_STAFF, self.ROLE_COUNSELOR)

    @property
    def is_church_admin(self):
        return self.role == self.ROLE_CHURCH_ADMIN

    @property
    def is_pastor(self):
        return self.role == self.ROLE_PASTOR

    @property
    def is_finance_officer(self):
        return self.role == self.ROLE_FINANCE_OFFICER

    @property
    def is_accountability_officer(self):
        """Alias used by the wellnessfund UI (Accountability Officer)."""
        return self.is_finance_officer

    @property
    def is_ministry_leader(self):
        return self.role == self.ROLE_MINISTRY_LEADER

    @property
    def is_counselor(self):
        return self.role == self.ROLE_COUNSELOR

    @property
    def is_member(self):
        return self.role == self.ROLE_CHURCH_MEMBER

    @property
    def is_donor(self):
        return self.role == self.ROLE_DONOR

    def clean(self):
        if not self.is_cfs_user and not self.church:
            from django.core.exceptions import ValidationError
            raise ValidationError("Church-scoped users must have a church assigned.")
