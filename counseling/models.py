from django.db import models
from django.utils import timezone


class Counselor(models.Model):
    """Counselor roster (CFS counselors assignable to pastors)."""
    user = models.OneToOneField('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='counselor_profile')
    full_name = models.CharField(max_length=150)
    speciality = models.CharField(max_length=150, blank=True)
    available = models.BooleanField(default=True)
    sessions_total = models.PositiveIntegerField(default=0)
    active_cases = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name


class CounselingCase(models.Model):
    """A counseling relationship/case between a pastor and counselor (or unassigned crisis)."""
    STATUS_CHOICES = [
        ('Unassigned', 'Unassigned'),
        ('Active', 'Active'),
        ('On Hold', 'On Hold'),
        ('Closed', 'Closed'),
    ]
    PRIORITY_CHOICES = [('high', 'high'), ('medium', 'medium'), ('normal', 'normal')]

    church = models.ForeignKey('churches.Church', on_delete=models.CASCADE, related_name='counseling_cases')
    pastor = models.ForeignKey('churches.Pastor', on_delete=models.CASCADE, related_name='counseling_cases')
    counselor = models.ForeignKey(Counselor, on_delete=models.SET_NULL, null=True, blank=True, related_name='cases')
    type = models.CharField(max_length=30, default='Regular')  # Crisis / Regular / Initial / Follow-up
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unassigned')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        cname = self.counselor.full_name if self.counselor else 'Unassigned'
        return f"Case: {self.pastor.full_name} with {cname}"


class CounselingSession(models.Model):
    """Individual session record (scheduled or completed)."""
    STATUS_CHOICES = [('Unassigned', 'Unassigned'), ('Scheduled', 'Scheduled'), ('Completed', 'Completed'), ('Pending', 'Pending')]

    case = models.ForeignKey(CounselingCase, on_delete=models.CASCADE, related_name='sessions')
    date = models.CharField(max_length=50, blank=True)  # e.g. 'Jul 15, 2025' or 'Urgent'
    time = models.CharField(max_length=30, blank=True)
    type = models.CharField(max_length=30, default='Regular')
    format = models.CharField(max_length=30, default='Video Call')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Scheduled')
    topic = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.date} - {self.case}"
