from datetime import datetime, timezone as dt_timezone
import hashlib
import json

import stripe
from django.conf import settings
from django.utils import timezone
from rest_framework import status

from apps.sub.models import BillingHistory, PrintOrder, StripeWebhookEvent, Subscription
from apps.sub.services.exceptions import ServiceError
from apps.sub.services.stripe_service import CREDIT_PACKAGES, StripeService
from apps.sub.tasks import process_order_paid, process_subscription_renewal, process_successful_credit_purchase


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


class PaymentService:
    @staticmethod
    def _extract_period_bounds(data):
        source = _as_dict(data)
        start = source.get("current_period_start")
        end = source.get("current_period_end")

        if start is None or end is None:
            items = ((source.get("items") or {}).get("data") or [])
            if items:
                first_item = _as_dict(items[0])
                start = start or first_item.get("current_period_start")
                end = end or first_item.get("current_period_end")

        if start is None or end is None:
            latest_invoice = _as_dict(source.get("latest_invoice") or {})
            lines = ((latest_invoice.get("lines") or {}).get("data") or [])
            if lines:
                period = (_as_dict(lines[0]).get("period") or {})
                start = start or period.get("start")
                end = end or period.get("end")

        return start, end

    @staticmethod
    def sync_subscription_periods(subscription):
        if not subscription or not subscription.stripe_subscription_id:
            return subscription

        stripe_sub = stripe.Subscription.retrieve(
            subscription.stripe_subscription_id,
            expand=["latest_invoice.lines"],
        )
        period_start_ts, period_end_ts = PaymentService._extract_period_bounds(stripe_sub)

        if period_start_ts is None or period_end_ts is None:
            invoices = stripe.Invoice.list(
                subscription=subscription.stripe_subscription_id,
                limit=1,
                expand=["data.lines"],
            )
            invoice_data = (_as_dict(invoices).get("data") or [])
            if invoice_data:
                latest_invoice = _as_dict(invoice_data[0])
                period_start_ts = period_start_ts or latest_invoice.get("period_start")
                period_end_ts = period_end_ts or latest_invoice.get("period_end")
                lines = ((latest_invoice.get("lines") or {}).get("data") or [])
                if lines:
                    period = (_as_dict(lines[0]).get("period") or {})
                    period_start_ts = period_start_ts or period.get("start")
                    period_end_ts = period_end_ts or period.get("end")

        if (period_start_ts is None or period_end_ts is None) and subscription.stripe_customer_id:
            try:
                upcoming = stripe.Invoice.upcoming(
                    customer=subscription.stripe_customer_id,
                    subscription=subscription.stripe_subscription_id,
                )
                upcoming_dict = _as_dict(upcoming)
                period_start_ts = period_start_ts or upcoming_dict.get("period_start")
                period_end_ts = period_end_ts or upcoming_dict.get("period_end")
                upcoming_lines = ((upcoming_dict.get("lines") or {}).get("data") or [])
                if upcoming_lines:
                    period = (_as_dict(upcoming_lines[0]).get("period") or {})
                    period_start_ts = period_start_ts or period.get("start")
                    period_end_ts = period_end_ts or period.get("end")
            except Exception:
                # Keep endpoint resilient; caller can still return existing DB values.
                pass

        updates = {}
        if period_start_ts:
            updates["current_period_start"] = datetime.fromtimestamp(period_start_ts, tz=dt_timezone.utc)
        if period_end_ts:
            updates["current_period_end"] = datetime.fromtimestamp(period_end_ts, tz=dt_timezone.utc)

        if updates:
            Subscription.objects.filter(id=subscription.id).update(**updates)
            for field, value in updates.items():
                setattr(subscription, field, value)

        return subscription

    @staticmethod
    def create_credit_checkout(user, credit_package, request=None):
        billing = BillingHistory.objects.create(
            user=user,
            billing_type=BillingHistory.BillingType.CREDIT_PURCHASE,
            amount=credit_package.price,
            status=BillingHistory.Status.PENDING,
            metadata={"credits": credit_package.credit_amount, "package_id": credit_package.id},
        )

        # Always use dynamic pricing based on model data
        line_items = [
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"{credit_package.credit_amount} Credits"},
                    "unit_amount": int(credit_package.price * 100),
                },
                "quantity": 1,
            }
        ]

        session = StripeService.create_checkout_session(
            user=user,
            mode="payment",
            success_path="/payment/success",
            cancel_path="/payment/cancel",
            line_items=line_items,
            metadata={"flow": "credit_purchase", "billing_history_id": str(billing.id)},
        )

        try:
            from apps.core.services.meta_pixel_service import send_meta_capi_event
            send_meta_capi_event(
                event_name="InitiateCheckout",
                user_email=user.email,
                value=float(credit_package.price),
                currency="USD",
                request=request,
                event_id=f"checkout_{session.id}",
                custom_data={
                    "content_type": "product",
                    "content_name": f"{credit_package.credit_amount} Credits Bundle",
                    "content_category": "credits_bundle"
                }
            )
        except Exception:
            pass

        billing.stripe_session_id = session.id
        billing.save(update_fields=["stripe_session_id"])
        return session.url

    @staticmethod
    def create_subscription_checkout(user, request=None):
        if not settings.STRIPE_SUBSCRIPTION_PRICE_29:
            raise ServiceError("Stripe subscription price is not configured", code="stripe_config")

        billing = BillingHistory.objects.create(
            user=user,
            billing_type=BillingHistory.BillingType.SUBSCRIPTION,
            amount=29,
            status=BillingHistory.Status.PENDING,
            metadata={"plan": "monthly_29", "credits": 300},
        )

        session = StripeService.create_checkout_session(
            user=user,
            mode="subscription",
            success_path="/subscription/success",
            cancel_path="/subscription/cancel",
            line_items=[{"price": settings.STRIPE_SUBSCRIPTION_PRICE_29, "quantity": 1}],
            metadata={"flow": "subscription", "billing_history_id": str(billing.id)},
        )

        try:
            from apps.core.services.meta_pixel_service import send_meta_capi_event
            send_meta_capi_event(
                event_name="InitiateCheckout",
                user_email=user.email,
                value=29.00,
                currency="USD",
                request=request,
                event_id=f"checkout_{session.id}",
                custom_data={
                    "content_type": "product",
                    "content_name": "iMVIO Pro Monthly Subscription",
                    "content_category": "subscription"
                }
            )
        except Exception:
            pass

        billing.stripe_session_id = session.id
        billing.save(update_fields=["stripe_session_id"])
        return session.url

    @staticmethod
    def create_print_order_checkout(*, user, order, request=None):
        session = StripeService.create_checkout_session(
            user=user,
            mode="payment",
            success_path="/orders/success",
            cancel_path="/orders/cancel",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"Print order #{order.id}"},
                        "unit_amount": int(order.amount * 100),
                    },
                    "quantity": 1,
                }
            ],
            metadata={"flow": "print_order", "order_id": str(order.id)},
            client_reference_id=str(order.id),
        )

        try:
            from apps.core.services.meta_pixel_service import send_meta_capi_event
            send_meta_capi_event(
                event_name="InitiateCheckout",
                user_email=user.email,
                value=float(order.amount),
                currency="USD",
                request=request,
                event_id=f"checkout_{session.id}",
                custom_data={
                    "content_type": "product",
                    "content_name": f"Print Order #{order.id}",
                    "content_category": "print_order"
                }
            )
        except Exception:
            pass

        order.stripe_session_id = session.id
        order.save(update_fields=["stripe_session_id", "updated_at"])

        BillingHistory.objects.create(
            user=user,
            billing_type=BillingHistory.BillingType.PRINT_ORDER,
            amount=order.amount,
            status=BillingHistory.Status.PENDING,
            stripe_session_id=session.id,
            metadata={"order_id": order.id},
        )

        return session.url

    @staticmethod
    def handle_stripe_webhook(payload, signature):
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise ServiceError("Stripe webhook secret is not configured", code="stripe_config")

        try:
            event = stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
        except Exception as exc:
            raise ServiceError(str(exc), status_code=status.HTTP_400_BAD_REQUEST, code="invalid_webhook")

        try:
            event_dict = json.loads(payload.decode("utf-8"))
        except Exception:
            event_dict = _as_dict(event)

        event_id = event_dict.get("id") or getattr(event, "id", "")
        event_type = event_dict.get("type") or getattr(event, "type", "")

        if not event_id:
            payload_hash = hashlib.sha256(payload).hexdigest()
            event_id = f"payload-{payload_hash}"

        webhook_event, created = StripeWebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "payload": event_dict,
                "status": StripeWebhookEvent.Status.PENDING,
            },
        )

        if not created:
            return

        try:
            PaymentService._process_stripe_event(event_dict)
            webhook_event.status = StripeWebhookEvent.Status.PROCESSED
            webhook_event.processed_at = timezone.now()
            webhook_event.save(update_fields=["status", "processed_at", "updated_at"])
        except Exception as exc:
            webhook_event.status = StripeWebhookEvent.Status.FAILED
            webhook_event.error_message = str(exc)
            webhook_event.save(update_fields=["status", "error_message", "updated_at"])
            raise

    @staticmethod
    def _process_stripe_event(event):
        event_type = event.get("type")

        if event_type == "checkout.session.completed":
            session = ((event.get("data") or {}).get("object") or {})
            metadata = session.get("metadata") or {}
            flow = metadata.get("flow")
            session_id = session.get("id")

            if flow == "credit_purchase":
                billing_id = metadata.get("billing_history_id")
                if billing_id:
                    process_successful_credit_purchase(int(billing_id))

            elif flow == "subscription":
                billing_id = metadata.get("billing_history_id")
                subscription_id = session.get("subscription")
                customer_id = session.get("customer")
                billing = BillingHistory.objects.filter(id=billing_id).first() if billing_id else None
                if billing and subscription_id:
                    invoice_id = session.get("invoice")
                    invoice_url = ""
                    if invoice_id:
                        invoice_obj = stripe.Invoice.retrieve(invoice_id)
                        invoice_dict = _as_dict(invoice_obj)
                        invoice_url = invoice_dict.get("invoice_pdf") or invoice_dict.get("hosted_invoice_url") or ""

                    stripe_sub = stripe.Subscription.retrieve(
                        subscription_id,
                        expand=["latest_invoice.lines"],
                    )

                    if not invoice_id:
                        latest_invoice_obj = _as_dict(stripe_sub).get("latest_invoice") or {}
                        invoice_id = latest_invoice_obj.get("id") or ""
                        invoice_url = latest_invoice_obj.get("invoice_pdf") or latest_invoice_obj.get("hosted_invoice_url") or ""

                    current_period_start, current_period_end = PaymentService._extract_period_bounds(stripe_sub)
                    
                    Subscription.objects.filter(user=billing.user).update(
                        stripe_customer_id=customer_id or "",
                        stripe_subscription_id=subscription_id,
                        package="package-1",
                        billing_interval="monthly",
                        is_active=True,
                        auto_renew=True,
                        current_period_start=datetime.fromtimestamp(current_period_start, tz=dt_timezone.utc) if current_period_start else None,
                        current_period_end=datetime.fromtimestamp(current_period_end, tz=dt_timezone.utc) if current_period_end else None,
                    )
                    if not Subscription.objects.filter(user=billing.user).exists():
                        Subscription.objects.create(
                            user=billing.user,
                            stripe_customer_id=customer_id or "",
                            stripe_subscription_id=subscription_id,
                            package="package-1",
                            billing_interval="monthly",
                            is_active=True,
                            auto_renew=True,
                            current_period_start=datetime.fromtimestamp(current_period_start, tz=dt_timezone.utc) if current_period_start else None,
                            current_period_end=datetime.fromtimestamp(current_period_end, tz=dt_timezone.utc) if current_period_end else None,
                        )

                    billing_updates = {}
                    if invoice_id and billing.stripe_invoice_id != invoice_id:
                        billing_updates["stripe_invoice_id"] = invoice_id
                    if invoice_url and billing.invoice_url != invoice_url:
                        billing_updates["invoice_url"] = invoice_url
                    if billing_updates:
                        BillingHistory.objects.filter(id=billing.id).update(**billing_updates)

                    process_subscription_renewal(int(billing.id))

            elif flow == "print_order":
                order_id = metadata.get("order_id")
                if not order_id and session.get("client_reference_id"):
                    order_id = session.get("client_reference_id")

                if not order_id and session_id:
                    billing = BillingHistory.objects.filter(stripe_session_id=session_id).first()
                    if billing:
                        order_id = str((billing.metadata or {}).get("order_id", ""))

                order = PrintOrder.objects.filter(id=order_id).first()
                if order:
                    process_order_paid(order.id)
                    BillingHistory.objects.filter(stripe_session_id=session_id).update(
                        status=BillingHistory.Status.PAID,
                        paid_at=timezone.now(),
                    )

        elif event_type == "invoice.payment_succeeded":
            invoice = ((event.get("data") or {}).get("object") or {})
            subscription_id = invoice.get("subscription")
            if subscription_id:
                sub = Subscription.objects.filter(stripe_subscription_id=subscription_id, is_active=True).first()
                if sub:
                    line_items = ((invoice.get("lines") or {}).get("data") or [])
                    invoice_period_start = None
                    invoice_period_end = None
                    if line_items:
                        invoice_period = (line_items[0] or {}).get("period") or {}
                        invoice_period_start = invoice_period.get("start")
                        invoice_period_end = invoice_period.get("end")

                    subscription_updates = {}
                    if invoice_period_start:
                        subscription_updates["current_period_start"] = datetime.fromtimestamp(invoice_period_start, tz=dt_timezone.utc)
                    if invoice_period_end:
                        subscription_updates["current_period_end"] = datetime.fromtimestamp(invoice_period_end, tz=dt_timezone.utc)
                    if subscription_updates:
                        Subscription.objects.filter(id=sub.id).update(**subscription_updates)

                    billing = BillingHistory.objects.create(
                        user=sub.user,
                        billing_type=BillingHistory.BillingType.SUBSCRIPTION,
                        amount=29,
                        status=BillingHistory.Status.PENDING,
                        stripe_invoice_id=invoice.get("id", ""),
                        invoice_url=invoice.get("invoice_pdf") or invoice.get("hosted_invoice_url", ""),
                        metadata={"renewal": True, "credits": 300},
                    )
                    process_subscription_renewal(billing.id)
