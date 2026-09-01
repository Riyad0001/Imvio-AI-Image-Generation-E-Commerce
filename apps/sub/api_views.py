import logging
from decimal import Decimal

from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
import stripe
from apps.sub.models import BillingHistory, PrintOrder, Subscription, CreditPackage, ProductSize
from apps.sub.serializers import (
    BillingHistorySerializer,
    BuyCreditsSerializer,
    PrintOrderCreateSerializer,
    PrintOrderSerializer,
    SubscribeSerializer,
    SubscriptionInfoSerializer,
    CreditPackageSerializer,
    ProductSizeSerializer,
)
from apps.sub.services.exceptions import ServiceError
from apps.sub.services.order_service import OrderService
from apps.sub.services.payment_service import PaymentService


logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


def _as_dict(value):
    if hasattr(value, "to_dict_recursive"):
        return value.to_dict_recursive()
    if hasattr(value, "_to_dict_recursive"):
        return value._to_dict_recursive()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return value
    return {}


class BuyCreditsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BuyCreditsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            package_id = serializer.validated_data["package_id"]
            credit_package = CreditPackage.objects.get(id=package_id)
            
            checkout_url = PaymentService.create_credit_checkout(
                user=request.user,
                credit_package=credit_package,
                request=request,
            )
            return Response(
                {
                    "status": True,
                    "message": "Credit checkout session created",
                    "data": {"checkout_url": checkout_url},
                }
            )
        except CreditPackage.DoesNotExist:
            return Response({"status": False, "message": "Credit package not found", "code": "PACKAGE_NOT_FOUND"}, status=404)
        except ServiceError as exc:
            return Response({"status": False, "message": exc.message, "code": exc.code}, status=exc.status_code)
        except Exception:
            logger.exception("buy_credits_failed")
            return Response({"status": False, "message": "Unable to create credit checkout"}, status=500)


class GetCreditPackagesView(APIView):
    authentication_classes= []
    permission_classes = [AllowAny] 

    def get(self, request):
        packages = CreditPackage.objects.filter().order_by("credit_amount")
        serializer = CreditPackageSerializer(packages, many=True)
        return Response(
            {
                "status": True,
                "message": "Credit packages fetched successfully",
                "data": serializer.data,
            }
        )


class GetProductSizesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sizes = ProductSize.objects.filter(is_active=True).order_by("id")
        serializer = ProductSizeSerializer(sizes, many=True)
        return Response(
            {
                "status": True,
                "message": "Product sizes fetched successfully",
                "data": serializer.data,
            }
        )


class SubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            checkout_url = PaymentService.create_subscription_checkout(user=request.user, request=request)
            return Response(
                {
                    "status": True,
                    "message": "Subscription checkout session created",
                    "data": {"checkout_url": checkout_url},
                }
            )
        except ServiceError as exc:
            return Response({"status": False, "message": exc.message, "code": exc.code}, status=exc.status_code)
        except Exception:
            logger.exception("subscribe_failed")
            return Response({"status": False, "message": "Unable to create subscription checkout"}, status=500)


class SubscriptionInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub = Subscription.objects.get(user=request.user, is_active=True)
        except Subscription.DoesNotExist:
            return Response({"status": True, "message": "No active subscription", "data": None})

        if (sub.current_period_start is None or sub.current_period_end is None) and sub.stripe_subscription_id:
            try:
                sub = PaymentService.sync_subscription_periods(sub)
            except Exception:
                logger.exception("subscription_period_sync_failed", extra={"subscription_id": sub.stripe_subscription_id})

        return Response(
            {
                "status": True,
                "message": "Subscription info fetched successfully",
                "data": SubscriptionInfoSerializer(sub).data,
            }
        )


class BillingHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = BillingHistory.objects.filter(user=request.user, status=BillingHistory.Status.PAID)
        active_sub = Subscription.objects.filter(user=request.user, is_active=True).first()
        customer_invoices = []
        used_invoice_ids = {billing.stripe_invoice_id for billing in queryset if billing.stripe_invoice_id}

        if active_sub and active_sub.stripe_customer_id:
            try:
                invoice_list = stripe.Invoice.list(customer=active_sub.stripe_customer_id, limit=100)
                customer_invoices = _as_dict(invoice_list).get("data") or []
            except Exception:
                logger.exception("billing_history_invoice_list_failed", extra={"customer_id": active_sub.stripe_customer_id})

        for billing in queryset:
            try:
                resolved_invoice_id = billing.stripe_invoice_id
                resolved_url = billing.invoice_url
                payment_intent_id = ""

                if not resolved_invoice_id and billing.stripe_session_id:
                    try:
                        session = stripe.checkout.Session.retrieve(billing.stripe_session_id)
                        session_dict = _as_dict(session)
                        resolved_invoice_id = session_dict.get("invoice") or ""
                        payment_intent_id = session_dict.get("payment_intent") or ""
                    except stripe.error.InvalidRequestError:
                        # Older session IDs may not exist in current Stripe account/mode.
                        resolved_invoice_id = ""

                if not resolved_invoice_id and billing.billing_type == BillingHistory.BillingType.SUBSCRIPTION and active_sub:
                    billing_amount_cents = int(Decimal(str(billing.amount)) * 100)
                    billing_created_ts = int(billing.created_at.timestamp()) if billing.created_at else 0

                    candidates = [
                        inv for inv in customer_invoices
                        if inv.get("id") not in used_invoice_ids
                        and inv.get("subscription") == active_sub.stripe_subscription_id
                    ]

                    def _score(inv):
                        inv_amount = inv.get("amount_paid") or inv.get("amount_due") or 0
                        amount_delta = abs(inv_amount - billing_amount_cents)
                        created_delta = abs((inv.get("created") or 0) - billing_created_ts)
                        return (amount_delta, created_delta)

                    if candidates:
                        best = sorted(candidates, key=_score)[0]
                        resolved_invoice_id = best.get("id") or ""

                if resolved_invoice_id:
                    try:
                        stripe_invoice = stripe.Invoice.retrieve(resolved_invoice_id)
                        stripe_invoice_dict = _as_dict(stripe_invoice)
                        invoice_pdf = stripe_invoice_dict.get("invoice_pdf")
                        hosted_url = stripe_invoice_dict.get("hosted_invoice_url")
                        resolved_url = invoice_pdf or hosted_url or resolved_url or ""
                    except stripe.error.InvalidRequestError:
                        # Stale invoice ID in DB or different Stripe mode/account.
                        resolved_invoice_id = ""

                if not resolved_url and payment_intent_id:
                    try:
                        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id, expand=["latest_charge"])
                        payment_intent_dict = _as_dict(payment_intent)
                        latest_charge = _as_dict(payment_intent_dict.get("latest_charge") or {})
                        resolved_url = latest_charge.get("receipt_url") or ""
                    except stripe.error.InvalidRequestError:
                        resolved_url = resolved_url or ""

                update_fields = []
                if billing.stripe_invoice_id and not resolved_invoice_id:
                    billing.stripe_invoice_id = ""
                    update_fields.append("stripe_invoice_id")
                if resolved_invoice_id and billing.stripe_invoice_id != resolved_invoice_id:
                    billing.stripe_invoice_id = resolved_invoice_id
                    update_fields.append("stripe_invoice_id")
                if resolved_url and billing.invoice_url != resolved_url:
                    billing.invoice_url = resolved_url
                    update_fields.append("invoice_url")
                if update_fields:
                    billing.save(update_fields=update_fields)
                    if billing.stripe_invoice_id:
                        used_invoice_ids.add(billing.stripe_invoice_id)
            except Exception:
                logger.exception(
                    "billing_history_invoice_fetch_failed",
                    extra={"billing_id": billing.id, "stripe_invoice_id": billing.stripe_invoice_id},
                )

        return Response(
            {
                "status": True,
                "message": "Billing history fetched successfully",
                "data": BillingHistorySerializer(queryset, many=True).data,
            }
        )


class CreatePrintOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PrintOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = OrderService.create_order(user=request.user, validated_data=serializer.validated_data)
            checkout_url = PaymentService.create_print_order_checkout(user=request.user, order=order, request=request)
            return Response(
                {
                    "status": True,
                    "message": "Print order created",
                    "data": {
                        "order_id": order.id,
                        "amount": str(order.amount),
                        "checkout_url": checkout_url,
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        except ServiceError as exc:
            return Response({"status": False, "message": exc.message, "code": exc.code}, status=exc.status_code)
        except Exception:
            logger.exception("create_print_order_failed")
            return Response({"status": False, "message": "Unable to create print order"}, status=500)


class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = PrintOrder.objects.filter(user=request.user).exclude(status=PrintOrder.Status.PENDING)
        return Response(
            {
                "status": True,
                "message": "Orders fetched successfully",
                "data": PrintOrderSerializer(orders, many=True).data,
            }
        )


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = PrintOrder.objects.filter(user=request.user, id=order_id).first()
        if not order:
            return Response({"status": False, "message": "Order not found"}, status=404)
        return Response(
            {
                "status": True,
                "message": "Order details fetched successfully",
                "data": PrintOrderSerializer(order).data,
            }
        )


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        PaymentService.handle_stripe_webhook(payload, signature)
        return JsonResponse({"status": "ok"})
    except ServiceError as exc:
        logger.warning("stripe_webhook_service_error", extra={"code": exc.code, "error_message": exc.message})
        return JsonResponse({"error": exc.message, "code": exc.code}, status=exc.status_code)
    except Exception:
        logger.exception("stripe_webhook_failed")
        return JsonResponse({"error": "Webhook processing failed"}, status=500)
