from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin

@admin.register(User)
class SubscriptionAdmin(ModelAdmin):
    pass
@admin.register(CreditWallet)
class CreditWalletAdmin(ModelAdmin):
    list_display = ["user", "balance"]
    search_fields = ["user__full_name", "user__email"]

