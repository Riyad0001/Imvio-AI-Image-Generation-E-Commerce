from django.template.defaultfilters import default
import uuid
from django.db import models


class Plan(models.Model):
    plan_type = models.CharField(max_length=50, choices=[("vehicle", "Vehicle"), ("parts", "Parts")], default="vehicle")
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    interval = models.CharField(max_length=50, choices=[("month", "Monthly"), ])
    description = models.TextField(blank=True, null=True)
    free_trial = models.BooleanField(default=False)
    free_trial_days = models.IntegerField(default=0)

    stripe_price_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_product_id = models.CharField(max_length=255, blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Plan"
        verbose_name_plural = "Plans"

    def __str__(self):
        return self.name


class Feature(models.Model):
    key = models.CharField(max_length=100, unique=True)  # ex: ai_conversation
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class PlanFeature(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="plan_features")
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)

    # feature configuration
    is_enabled = models.BooleanField(default=True)
    limit_value = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("plan", "feature")



class Subscription(models.Model):
    user = models.ForeignKey(
        "account.User", on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name="subscriptions"
    )
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user} - {self.plan}"


