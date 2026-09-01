from unfold.admin import ModelAdmin
from .models import *
from django.contrib import admin
from apps.sub.models import *
@admin.register(ProductType)
class ProductTypeAdmin(ModelAdmin):
    list_display = ["id", "name"]


@admin.register(ProductVariant)
class ProductVariantAdmin(ModelAdmin):
    list_display = ["id", "product_type", "size", "gelato_product_uid", "price", "shipping_cost"]
    list_editable = ["gelato_product_uid", "price", "shipping_cost"]
    list_filter = ["product_type", "size"]
    search_fields = ["product_type__name", "size__display_size", "gelato_product_uid"]


@admin.register(Other_pages)
class Other_pagesAdmin(ModelAdmin):
    list_display = ["id", "name", "types", "created_at", "updated_at"]
    list_editable = ["types"]
    list_filter = ["types"]
    search_fields = ["name", "content"]
