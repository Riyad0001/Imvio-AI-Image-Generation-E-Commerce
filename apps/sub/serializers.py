from rest_framework import serializers

from apps.sub.models import BillingHistory, PrintOrder, Subscription, CreditPackage, ProductSize
from apps.product_mookup.models import ProductType, ProductVariant


class BuyCreditsSerializer(serializers.Serializer):
    package_id = serializers.IntegerField()

    def validate_package_id(self, value):
        try:
            CreditPackage.objects.get(id=value)
        except CreditPackage.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive credit package.")
        return value


class CreditPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditPackage
        fields = [
            "id",
            "title",
            "subtitle",
            "description",
            "credit_amount",
            "price",
            "features",
            "is_featured",
        ]


class SubscribeSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=["monthly_29"])


class ProductSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSize
        fields = ["id", "display_size", "gelato_size", "gelato_product_uid", "is_active"]


class PrintOrderCreateSerializer(serializers.Serializer):
    generated_image_id = serializers.IntegerField()
    product_type_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductType.objects.all(),
        source="product_type_obj",
    )
    size_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductSize.objects.filter(is_active=True),
        source="product_size"
    )
    shipping_address = serializers.JSONField()

    def validate_shipping_address(self, value):
        required_keys = ["name", "address_line1", "city", "country", "postal_code"]
        for key in required_keys:
            if key not in value or not str(value.get(key, "")).strip():
                raise serializers.ValidationError(f"Missing or empty required field: {key}")
        
        # Validate postal_code is not empty and is a string
        postal_code = str(value.get("postal_code", "")).strip()
        if not postal_code:
            raise serializers.ValidationError("postal_code cannot be empty")
        value["postal_code"] = postal_code
        
        return value


class BillingHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingHistory
        fields = [
            "id",
            "billing_type",
            "amount",
            "currency",
            "stripe_invoice_id",
            "invoice_url",
            "status",
            "created_at",
            "paid_at",
        ]


class SubscriptionInfoSerializer(serializers.ModelSerializer):
    total_available_credits = serializers.SerializerMethodField()
    next_renewal_date = serializers.DateTimeField(source="current_period_end", allow_null=True)
    current_period_start = serializers.DateTimeField(allow_null=True)

    class Meta:
        model = Subscription
        fields = [
            "package",
            "billing_interval",
            "is_active",
            "total_available_credits",
            "current_period_start",
            "next_renewal_date",
        ]

    def get_total_available_credits(self, obj):
        wallet = getattr(obj.user, "wallet", None)
        return wallet.balance if wallet else 0


class PrintOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintOrder
        fields = "__all__"
        read_only_fields = ["user", "stripe_session_id", "gelato_order_id", "status", "created_at", "updated_at"]
