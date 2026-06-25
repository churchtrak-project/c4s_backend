import uuid

from django.db import models
from django.utils import timezone


class Church(models.Model):
    """
    Tenant root. Every other record (campaigns, donations, users, etc.) belongs to a Church.
    Self-signup creates one of these + initial admin + pastor.
    """
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True, help_text="Used in URLs / public links")
    county = models.CharField(max_length=100, blank=True, help_text="Kenya county for localization")
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)

    # Platform control
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Internal CFS notes")

    # Frontend-aligned denormalized / subscription fields (updated by admin or computed in views)
    PLAN_STARTER = 'Starter'
    PLAN_GROWTH = 'Growth'
    PLAN_ENTERPRISE = 'Enterprise'
    PLAN_CHOICES = [
        (PLAN_STARTER, 'Starter'),
        (PLAN_GROWTH, 'Growth'),
        (PLAN_ENTERPRISE, 'Enterprise'),
    ]
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default=PLAN_STARTER)
    member_count = models.PositiveIntegerField(default=0)
    wellness_avg = models.PositiveIntegerField(default=50)  # 0-100 average across pastors
    current_fund_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Churches"

    def __str__(self):
        return self.name


class Pastor(models.Model):
    """
    One primary pastor per church (as per current requirements).
    This is the main beneficiary of the Pastoral Wellness Fund.
    Can optionally have a login User (role=pastor).
    """
    church = models.OneToOneField(
        Church,
        on_delete=models.CASCADE,
        related_name='pastor'
    )
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pastor_profile',
        help_text="Optional login account for the pastor themselves"
    )

    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    # Wellness & status snapshot (powers CFS pastors list + at-risk + pastor dashboards)
    wellness_score = models.PositiveIntegerField(default=50)  # 0-100
    last_rest_date = models.DateField(null=True, blank=True)
    years_of_service = models.PositiveIntegerField(default=0)
    total_retreats_taken = models.PositiveIntegerField(default=0)

    # Counselor assignment (simple FK for now; can be User with counselor role)
    counselor = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_pastors',
        limit_choices_to={'role__in': ['counselor', 'cfs_counselor']},  # relaxed
    )
    counselor_name = models.CharField(max_length=150, blank=True)  # denorm for display when no user

    # Status for filtering / alerts
    STATUS_HEALTHY = 'Healthy'
    STATUS_STABLE = 'Stable'
    STATUS_MONITOR = 'Monitor'
    STATUS_AT_RISK = 'At Risk'
    STATUS_CHOICES = [
        (STATUS_HEALTHY, 'Healthy'),
        (STATUS_STABLE, 'Stable'),
        (STATUS_MONITOR, 'Monitor'),
        (STATUS_AT_RISK, 'At Risk'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_STABLE)
    assessment_due = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Pastor {self.full_name} ({self.church.name})"

    @property
    def last_rest_display(self):
        if not self.last_rest_date:
            return 'Never'
        from datetime import date
        days = (date.today() - self.last_rest_date).days
        return f"{days} days ago" if days > 0 else 'Today'

    @property
    def counselor_display(self):
        if self.counselor:
            return self.counselor.full_name or self.counselor.email or self.counselor.phone
        return self.counselor_name or 'Unassigned'


# =============================================================================
# Additional operational models to support the full frontend (added to churches
# app for simplicity and tenant scoping). These power members, events, tasks,
# content/library/sermons, and wellness assessments visible across roles.
# =============================================================================

class Member(models.Model):
    """Church member directory (church-admin/members, ministry-leader/members)."""
    church = models.ForeignKey(Church, on_delete=models.CASCADE, related_name='members')
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    county = models.CharField(max_length=100, blank=True)
    cell_group = models.CharField(max_length=100, blank=True)
    ministry = models.CharField(max_length=100, blank=True)
    attendance = models.CharField(max_length=50, default='Regular')  # Regular / Irregular / Absent ×3
    baptized = models.BooleanField(default=False)
    status = models.CharField(max_length=30, default='Active')  # Active / Follow-up
    joined = models.CharField(max_length=50, blank=True)  # e.g. 'Jan 2020' or date
    email = models.EmailField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.church.name})"


class ChurchEvent(models.Model):
    """Events for both CFS platform events and per-church events."""
    EVENT_TYPE_CHOICES = [
        ('Conference', 'Conference'),
        ('Webinar', 'Webinar'),
        ('Retreat', 'Retreat'),
        ('Workshop', 'Workshop'),
        ('Service', 'Service'),
        ('Other', 'Other'),
    ]
    FORMAT_CHOICES = [
        ('In-person', 'In-person'),
        ('Online', 'Online'),
        ('Hybrid', 'Hybrid'),
    ]
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Almost Full', 'Almost Full'),
        ('Planning', 'Planning'),
        ('Closed', 'Closed'),
        ('Recurring', 'Recurring'),
    ]

    church = models.ForeignKey(Church, on_delete=models.CASCADE, related_name='events', null=True, blank=True)
    # If null, it's a global CFS event (visible in cfs-admin/events)
    title = models.CharField(max_length=200)
    type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES, default='Other')
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='In-person')
    date = models.CharField(max_length=100, blank=True)  # human readable or range for FE simplicity
    location = models.CharField(max_length=200, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    registered = models.PositiveIntegerField(default=0)
    fee = models.CharField(max_length=50, default='Free')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    is_cfs_event = models.BooleanField(default=False)  # true for platform-wide

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        scope = 'CFS' if self.is_cfs_event else (self.church.name if self.church else '—')
        return f"{self.title} [{scope}]"


class Task(models.Model):
    """Assignable tasks across roles (pastor, church-admin, ministry-leader, finance, etc.)."""
    PRIORITY_CHOICES = [('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')]
    STATUS_CHOICES = [('Pending', 'Pending'), ('In Progress', 'In Progress'), ('Done', 'Done')]

    church = models.ForeignKey(Church, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    title = models.CharField(max_length=200)
    assigned_to = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    assignee_name = models.CharField(max_length=150, blank=True)  # denorm
    due_date = models.CharField(max_length=50, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    done = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ContentResource(models.Model):
    """Knowledge base / sermons / articles / toolkits (cfs-admin/content, pastor/sermons, member/library)."""
    TYPE_CHOICES = [('Article', 'Article'), ('Video', 'Video'), ('Audio', 'Audio'), ('Toolkit', 'Toolkit')]
    STATUS_CHOICES = [('Draft', 'Draft'), ('Published', 'Published')]

    church = models.ForeignKey(Church, on_delete=models.CASCADE, related_name='resources', null=True, blank=True)
    is_cfs = models.BooleanField(default=True)  # platform content vs local
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=150, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Article')
    category = models.CharField(max_length=100, blank=True)
    audience = models.CharField(max_length=50, blank=True)  # Pastors / Congregation / Families
    views = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    date = models.CharField(max_length=50, blank=True)  # e.g. 'Jun 2025'

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class WellnessAssessment(models.Model):
    """Monthly pastor self-assessment (pastor/wellness). Stores answers + computed scores."""
    pastor = models.ForeignKey(Pastor, on_delete=models.CASCADE, related_name='assessments')
    assessment_date = models.DateField(auto_now_add=True)
    answers = models.JSONField(default=dict, blank=True)  # {q1: 'Agree', ...}
    overall_score = models.PositiveIntegerField(default=50)
    dimension_scores = models.JSONField(default=dict, blank=True)  # {'Physical Rest': 45, ...}
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-assessment_date']

    def __str__(self):
        return f"Assessment for {self.pastor.full_name} on {self.assessment_date}"
