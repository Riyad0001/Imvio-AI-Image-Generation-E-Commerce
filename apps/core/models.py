from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
import uuid


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('full_name', 'Admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class ActiveUserQuerySet(QuerySet):
    def active(self):
        return self.filter(is_deleted=False)


class ActiveUserManager(UserManager):
    def get_queryset(self):
        return ActiveUserQuerySet(self.model, using=self._db).active()


class AllUserManager(UserManager):
    pass

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=32, blank=True)
    profile_photo = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_disabled = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveUserManager()
    all_objects = AllUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def serialize(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone_number": self.phone_number,
            "profile_photo": self.profile_photo.url if self.profile_photo else None,
            "is_disabled": self.is_disabled,
            "is_deleted": self.is_deleted,
        }

    def disable(self):
        self.is_disabled = True
        self.is_active = False
        self.save(update_fields=["is_disabled", "is_active", "updated_at"])

    def soft_delete(self):
        if self.email and not self.email.endswith("@deleted.local"):
            self.email = f"deleted-{self.pk}-{uuid.uuid4().hex[:8]}@deleted.local"

        self.is_deleted = True
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=["email", "is_deleted", "is_active", "deleted_at", "updated_at"])


class CreditWallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.balance} credits"


class CreditTransaction(models.Model):
    class EntryType(models.TextChoices):
        CREDIT_IN = "credit_in", "Credit In"
        CREDIT_OUT = "credit_out", "Credit Out"

    class Source(models.TextChoices):
        IMAGE_GENERATION = "image_generation", "Image Generation"
        IMAGE_DOWNLOAD = "image_download", "Image Download"
        CREDIT_PURCHASE = "credit_purchase", "Credit Purchase"
        SUBSCRIPTION_RENEWAL = "subscription_renewal", "Subscription Renewal"
        SIGNUP_BONUS = "signup_bonus", "Signup Bonus"
        REFUND = "refund", "Refund"
        MANUAL = "manual", "Manual"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="credit_transactions")
    wallet = models.ForeignKey(CreditWallet, on_delete=models.CASCADE, related_name="transactions")
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    source = models.CharField(max_length=32, choices=Source.choices)
    amount = models.PositiveIntegerField()
    balance_after = models.PositiveIntegerField()
    reference = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} {self.entry_type} {self.amount}"
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        from django.utils.timezone import now
        if not self.created_at:
            return True
        age_seconds = (now() - self.created_at).total_seconds()
        if age_seconds < 0:
            return False
        return age_seconds > 300