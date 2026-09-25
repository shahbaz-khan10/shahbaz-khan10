from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.utils import timezone


class User(AbstractBaseUser):
    """A login identity. Every non-system user is linked to an Employee."""

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_accounts",
    )
    username = models.CharField(max_length=64, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    password_hash = models.CharField(max_length=255)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []
    is_super_admin = models.BooleanField(
        default=False, help_text="Platform root account — bypasses all permission checks."
    )
    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        if self.employee_id:
            return self.employee.full_name
        return self.username

    @property
    def department(self):
        if self.employee_id:
            return self.employee.department
        return None

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def is_locked(self):
        return self.locked_until is not None and self.locked_until > timezone.now()

    def record_failed_login(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= settings.MAX_FAILED_LOGINS:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
        self.save(update_fields=["failed_login_attempts", "locked_until", "updated_at"])

    def record_successful_login(self):
        self.last_login_at = timezone.now()
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=["last_login_at", "failed_login_attempts", "locked_until", "updated_at"])


class RefreshToken(models.Model):
    """Server-side record of an issued refresh token (stored as a hash)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    @property
    def is_valid(self):
        if self.revoked_at:
            return False
        if self.expires_at < timezone.now():
            return False
        return True

    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])


class BlacklistedToken(models.Model):
    """Rendered JWT jtis that can no longer be used (logout)."""

    jti = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blacklisted_tokens")
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["jti"])]