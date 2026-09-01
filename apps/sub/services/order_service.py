from decimal import Decimal

from django.conf import settings
from django.db import transaction
from rest_framework import status

from apps.image_gen.models import GeneratedImage
from apps.sub.models import PrintOrder
from apps.sub.services.exceptions import ServiceError
from apps.product_mookup.models import ProductVariant


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(user, validated_data):
        generated_image_id = validated_data["generated_image_id"]
        image = GeneratedImage.objects.filter(
            id=generated_image_id,
            user=user,
            is_deleted=False,
        ).first()
        if not image:
            raise ServiceError(
                "Invalid image selected for print order",
                status_code=status.HTTP_404_NOT_FOUND,
                code="image_not_found",
            )

        # Get the selected product size and product type
        product_size = validated_data["product_size"]
        product_type_obj = validated_data["product_type_obj"]

        print(f"[ORDER SERVICE] Selected size: {product_size.display_size}")
        print(f"[ORDER SERVICE] Selected product type: {product_type_obj.name}")

        # Look up dynamic pricing and Gelato product UID from ProductVariant
        try:
            variant = ProductVariant.objects.get(
                product_type=product_type_obj,
                size=product_size,
            )
        except ProductVariant.DoesNotExist:
            raise ServiceError(
                "No pricing found for this product type and size combination",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="variant_not_found",
            )

        gelato_product_uid = variant.gelato_product_uid
        print(f"[ORDER SERVICE] Using Gelato product UID: {gelato_product_uid}")

        supported_product_uids = getattr(settings, "GELATO_SUPPORTED_PRODUCT_UIDS", [])
        if supported_product_uids and gelato_product_uid not in supported_product_uids:
            raise ServiceError(
                "Unsupported product_type for Gelato",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="unsupported_product_uid",
            )

        amount = variant.price + variant.shipping_cost

        print(f"[ORDER SERVICE] Price: {variant.price}, Shipping: {variant.shipping_cost}, Total: {amount}")

        order = PrintOrder.objects.create(
            user=user,
            generated_image_id=generated_image_id,
            product_type=gelato_product_uid,
            product_type_ref=product_type_obj,
            product_size=product_size,
            shipping_address=validated_data["shipping_address"],
            amount=amount,
        )
        return order
