from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Custom user with role-based access."""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('guard', 'Security Guard / Receptionist'),
        ('employee', 'Employee / Host'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    phone = models.CharField(max_length=15, blank=True)
    department = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class Visitor(models.Model):
    """Visitor profile — created once, referenced by visits."""
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15)
    company = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)
    id_proof_type = models.CharField(
        max_length=50, blank=True,
        choices=[('aadhar', 'Aadhar'), ('passport', 'Passport'),
                 ('driving_license', 'Driving License'), ('other', 'Other')]
    )
    id_proof_number = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(upload_to='visitor_photos/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='registered_visitors')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Visit(models.Model):
    """Each visit instance — tracks check-in/check-out."""
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
    ]
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='visits')
    host = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='hosted_visits')
    purpose = models.CharField(max_length=300)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    badge_number = models.CharField(max_length=20, blank=True)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.visitor.name} → {self.host} ({self.get_status_display()})"

    @property
    def duration(self):
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{hours}h {minutes}m"
        return None


class Notification(models.Model):
    """In-app notifications for hosts."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}"


class Blacklist(models.Model):
    """Blacklisted visitors who are denied entry."""
    visitor = models.OneToOneField(Visitor, on_delete=models.CASCADE, related_name='blacklist_entry')
    reason = models.TextField()
    blacklisted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"BLACKLISTED: {self.visitor.name} — {self.reason[:50]}"
