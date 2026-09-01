from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()


def _get_product_type_model():
    """Lazy import to avoid circular dependency."""
    from apps.product_mookup.models import ProductType
    return ProductType


class Subscription(models.Model):
    PACKAGE_CHOICES = [("package-1", "Package 1"), ("package-2", "Package 2")]
    BILLING_CHOICES = [("monthly", "Monthly"), ("yearly", "Yearly")]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=255)
    stripe_subscription_id = models.CharField(max_length=255)
    package = models.CharField(max_length=20, choices=PACKAGE_CHOICES)
    billing_interval = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=True)
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return self.user.email + " - " + self.package + " (" + self.billing_interval + ")"
    
class ProductSize(models.Model):
    display_size = models.CharField(max_length=50)  # "8x8", "24x32", etc for frontend
    gelato_size = models.CharField(max_length=100)  # Size code for Gelato (e.g., "200x200-mm-8x8-inch")
    gelato_product_uid = models.CharField(max_length=200)  # Complete Gelato product UID
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.display_size} ({self.gelato_size})"

class BillingHistory(models.Model):
    class BillingType(models.TextChoices):
        CREDIT_PURCHASE = "credit_purchase", "Credit Purchase"
        SUBSCRIPTION = "subscription", "Subscription"
        PRINT_ORDER = "print_order", "Print Order"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="billing_history")
    billing_type = models.CharField(max_length=32, choices=BillingType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="usd")
    stripe_session_id = models.CharField(max_length=255, blank=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True)
    invoice_url = models.URLField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]


class PrintOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SENT_TO_GELATO = "sent_to_gelato", "Sent to Gelato"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="print_orders")
    generated_image_id = models.PositiveIntegerField()
    product_type = models.CharField(max_length=100)  # Gelato product UID
    product_type_ref = models.ForeignKey(
        "product_mookup.ProductType", on_delete=models.SET_NULL,
        blank=True, null=True, related_name="print_orders",
        help_text="Reference to the ProductType selected by the user"
    )
    product_size = models.ForeignKey(ProductSize, on_delete=models.PROTECT, related_name="print_orders")
    shipping_address = models.JSONField(default=dict)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_session_id = models.CharField(max_length=255, blank=True)
    gelato_order_id = models.CharField(max_length=255, blank=True)
    gelato_error_message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class StripeWebhookEvent(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=128)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class CreditPackage(models.Model):
    title = models.CharField(max_length=100,blank=True,null=True)
    subtitle = models.CharField(max_length=255, blank=True,null=True)
    description = models.TextField(blank=True,null=True)
    credit_amount = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    features = models.JSONField(default=list, blank=True)  # Array of feature strings
    is_featured = models.BooleanField(default=False,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["credit_amount"]

    def __str__(self):
        return f"{self.credit_amount} credits - ${self.price}"


