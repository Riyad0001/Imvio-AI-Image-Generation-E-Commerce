from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Subscription, PlanFeature, Plan, Feature


@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active')

@admin.register(PlanFeature)
class PlanFeatureAdmin(ModelAdmin):
    list_display = ('plan', 'feature', 'is_enabled', 'limit_value')

@admin.register(Plan)
class PlanAdmin(ModelAdmin):
    list_display = ('name', 'price', 'vat', 'interval', 'description', 'free_trial', 'free_trial_days')

@admin.register(Feature)
class FeatureAdmin(ModelAdmin):
    list_display = ('key', 'name', 'description')
