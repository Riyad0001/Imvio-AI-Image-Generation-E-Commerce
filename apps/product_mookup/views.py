from rest_framework.views import APIView
from rest_framework.response import Response
from .models import *
from .serializers import Other_pagesSerializer
from rest_framework.permissions import AllowAny
from apps.sub.models import *

class ProductTypeListAPIView(APIView):
    authentication_classes= []
    permission_classes = [AllowAny] 

    def get(self, request):

        types = ProductType.objects.all()

        data = []

        for item in types:
            data.append({
                "id": item.id,
                "name": item.name,
                "image": request.build_absolute_uri(
                    item.image.url
                )
            })

        return Response({
            "success": True,
            "data": data
        })

class ProductTypeSizeAPIView(APIView):
    authentication_classes= []
    permission_classes = [AllowAny] 

    def get(self, request, product_type_id):
        variants = ProductVariant.objects.filter(
            product_type_id=product_type_id
        ).select_related("size")

        data = []

        for item in variants:
            data.append({
                "id": item.size.id,
                "display_size": item.size.display_size,
                "gelato_size": item.size.gelato_size,
                "gelato_product_uid": item.gelato_product_uid,
                "is_active": item.size.is_active,
            })

        return Response({
            "success": True,
            "data": data
        })

class CalculatePriceAPIView(APIView):
    authentication_classes= []
    permission_classes = [AllowAny] 

    def post(self, request):

        product_type_id = request.data.get(
            "product_type_id"
        )

        size_id = request.data.get(
            "size_id"
        )

        variant = ProductVariant.objects.get(
            product_type_id=product_type_id,
            size_id=size_id
        )

        total = (
            variant.price +
            variant.shipping_cost
        )

        return Response({
            "success": True,
            "data": {
                "variant_id": variant.id,
                "price": variant.price,
                "shipping": variant.shipping_cost,
                "total": total
            }
        })


class ProductTypePricingAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, product_type_id):

        variants = ProductVariant.objects.filter(
            product_type_id=product_type_id
        ).select_related("size")

        data = []

        for variant in variants:
            total = variant.price + variant.shipping_cost
            data.append({
                "variant_id": variant.id,
                "size_id": variant.size.id,
                "size_name": variant.size.display_size,
                "price": variant.price,
                "shipping": variant.shipping_cost,
                "total": total
            })

        return Response({
            "success": True,
            "data": data
        })

class Other_pagesView(APIView):
    authentication_classes= []
    permission_classes = [AllowAny] 

    def get(self, request, type):
        pages = Other_pages.objects.filter(types=type).first()
        if not pages:
            return Response({
                "success": False,
                "message": "Page not found"
            }, status=404)
        serializer = Other_pagesSerializer(pages)
        return Response({
            "success": True,
            "data": serializer.data
        })

def dashboard_callback(request, context):
    # Import here to avoid circular issues at module level
    import apps.product_mookup.dashboard_components  # noqa: F401 – registers components

    from decimal import Decimal
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta

    from apps.core.models import User, CreditWallet
    from apps.sub.models import (
        Subscription, BillingHistory, PrintOrder, CreditPackage
    )
    from apps.image_gen.models import ImageGenerationJob, GeneratedImage
    from apps.designs.models import Contact, NewsletterSubscription

    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    # ── KPI Stats ──────────────────────────────────────────────────────────────
    total_users = User.all_objects.filter(is_deleted=False).count()
    new_users_30d = User.all_objects.filter(
        created_at__gte=thirty_days_ago, is_deleted=False
    ).count()
    active_subscriptions = Subscription.objects.filter(is_active=True).count()

    total_revenue = BillingHistory.objects.filter(
        status=BillingHistory.Status.PAID
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    revenue_30d = BillingHistory.objects.filter(
        status=BillingHistory.Status.PAID,
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    total_images = GeneratedImage.objects.filter(is_deleted=False).count()
    images_30d = ImageGenerationJob.objects.filter(
        created_at__gte=thirty_days_ago
    ).count()

    pending_orders = PrintOrder.objects.filter(
        status=PrintOrder.Status.PENDING
    ).count()
    total_orders = PrintOrder.objects.count()

    unread_contacts = Contact.objects.filter(is_read=False).count()
    total_contacts = Contact.objects.count()

    newsletter_subs = NewsletterSubscription.objects.filter(is_active=True).count()

    total_credits_in_wallets = CreditWallet.objects.aggregate(
        total=Sum("balance")
    )["total"] or 0

    # ── Billing breakdown ─────────────────────────────────────────────────────
    sub_revenue = BillingHistory.objects.filter(
        status=BillingHistory.Status.PAID,
        billing_type=BillingHistory.BillingType.SUBSCRIPTION,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    credit_revenue = BillingHistory.objects.filter(
        status=BillingHistory.Status.PAID,
        billing_type=BillingHistory.BillingType.CREDIT_PURCHASE,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    print_revenue = BillingHistory.objects.filter(
        status=BillingHistory.Status.PAID,
        billing_type=BillingHistory.BillingType.PRINT_ORDER,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # ── Recent rows for tables ─────────────────────────────────────────────────
    recent_orders = (
        PrintOrder.objects.select_related("user", "product_size")
        .order_by("-created_at")[:10]
    )

    recent_contacts = Contact.objects.order_by("-created_at")[:10]

    recent_billing = (
        BillingHistory.objects.select_related("user")
        .filter(status=BillingHistory.Status.PAID)
        .order_by("-created_at")[:8]
    )

    # ── Order status counts ────────────────────────────────────────────────────
    order_status_counts = {
        "pending":        PrintOrder.objects.filter(status=PrintOrder.Status.PENDING).count(),
        "paid":           PrintOrder.objects.filter(status=PrintOrder.Status.PAID).count(),
        "sent_to_gelato": PrintOrder.objects.filter(status=PrintOrder.Status.SENT_TO_GELATO).count(),
        "failed":         PrintOrder.objects.filter(status=PrintOrder.Status.FAILED).count(),
    }

    # ── Image job status counts ────────────────────────────────────────────────
    job_status_counts = {
        "pending":    ImageGenerationJob.objects.filter(status=ImageGenerationJob.Status.PENDING).count(),
        "processing": ImageGenerationJob.objects.filter(status=ImageGenerationJob.Status.PROCESSING).count(),
        "succeeded":  ImageGenerationJob.objects.filter(status=ImageGenerationJob.Status.SUCCEEDED).count(),
        "failed":     ImageGenerationJob.objects.filter(status=ImageGenerationJob.Status.FAILED).count(),
    }

    context.update({
        # KPI
        "total_users": total_users,
        "new_users_30d": new_users_30d,
        "active_subscriptions": active_subscriptions,
        "total_revenue": total_revenue,
        "revenue_30d": revenue_30d,
        "total_images": total_images,
        "images_30d": images_30d,
        "pending_orders": pending_orders,
        "total_orders": total_orders,
        "unread_contacts": unread_contacts,
        "total_contacts": total_contacts,
        "newsletter_subs": newsletter_subs,
        "total_credits_in_wallets": total_credits_in_wallets,
        # Revenue breakdown
        "sub_revenue": sub_revenue,
        "credit_revenue": credit_revenue,
        "print_revenue": print_revenue,
        # Tables
        "recent_orders": recent_orders,
        "recent_contacts": recent_contacts,
        "recent_billing": recent_billing,
        # Status counts
        "order_status_counts": order_status_counts,
        "job_status_counts": job_status_counts,
    })

    return context