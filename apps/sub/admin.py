from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin

@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = ["user","is_active"]
    search_fields = ["user__full_name", "package","user__email"]

@admin.register(PrintOrder)
class PrintOrderAdmin(ModelAdmin):
    pass
@admin.register(CreditPackage)
class CreditPackageAdmin(ModelAdmin):
    list_display = ["title", "price"]
    # search_fields = ["user__full_name", "credit_amount","user__email"]

@admin.register(ProductSize)
class ProductSizeAdmin(ModelAdmin):
    list_display = ["display_size", "gelato_size", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["display_size", "gelato_size"]

