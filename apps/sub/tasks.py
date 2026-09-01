from django.db import transaction
from django.utils import timezone
import logging

from apps.core.models import CreditTransaction, User
from apps.core.services.credits import add_credits
from apps.core.email_utils import (
    send_subscription_activated_email,
    send_credits_purchased_email,
    send_order_confirmed_email,
)
from apps.sub.models import BillingHistory, PrintOrder, Subscription
from apps.sub.services.gelato_service import GelatoService


logger = logging.getLogger(__name__)


def process_successful_credit_purchase(billing_history_id):
    with transaction.atomic():
        billing = BillingHistory.objects.select_for_update().get(id=billing_history_id)
        if billing.status == BillingHistory.Status.PAID:
            return

        credits = int((billing.metadata or {}).get("credits", 0))
        if credits <= 0:
            raise ValueError("Invalid credits amount in billing metadata")

        user = User.all_objects.get(id=billing.user_id)
        add_credits(
            user=user,
            amount=credits,
            source=CreditTransaction.Source.CREDIT_PURCHASE,
            reference=f"billing:{billing_history_id}",
        )
        billing.status = BillingHistory.Status.PAID
        billing.paid_at = timezone.now()
        billing.save(update_fields=["status", "paid_at"])

    # Send confirmation email (outside atomic block)
    try:
        from apps.core.services.credits import get_or_create_wallet
        wallet = get_or_create_wallet(user)
        send_credits_purchased_email(
            user=user,
            credits=credits,
            amount=float(billing.amount),
            total_balance=wallet.balance,
        )
    except Exception:
        logger.exception("credits_email_failed", extra={"billing_id": billing_history_id})

    # Send Meta CAPI event (outside atomic block)
    try:
        from apps.core.services.meta_pixel_service import send_meta_capi_event
        send_meta_capi_event(
            event_name="Purchase",
            user_email=user.email,
            value=float(billing.amount),
            currency=billing.currency or "USD",
            event_id=f"purchase_{billing.id}",
            custom_data={
                "content_type": "product",
                "content_name": f"{credits} Credits Bundle",
                "content_category": "credits_bundle"
            }
        )
    except Exception:
        logger.exception("capi_credits_purchase_failed", extra={"billing_id": billing_history_id})


def process_subscription_renewal(billing_history_id):
    with transaction.atomic():
        billing = BillingHistory.objects.select_for_update().get(id=billing_history_id)
        if billing.status == BillingHistory.Status.PAID:
            return

        credits = int((billing.metadata or {}).get("credits", 300))
        user = User.all_objects.get(id=billing.user_id)
        add_credits(
            user=user,
            amount=credits,
            source=CreditTransaction.Source.SUBSCRIPTION_RENEWAL,
            reference=f"subscription:{billing_history_id}",
        )
        billing.status = BillingHistory.Status.PAID
        billing.paid_at = timezone.now()
        billing.save(update_fields=["status", "paid_at"])

    # Send confirmation email (outside atomic block)
    try:
        send_subscription_activated_email(
            user=user,
            credits=credits,
            plan_name="iMVIO Pro",
            billing_interval="Monthly",
        )
    except Exception:
        logger.exception("subscription_email_failed", extra={"billing_id": billing_history_id})

    # Send Meta CAPI event (outside atomic block)
    try:
        from apps.core.services.meta_pixel_service import send_meta_capi_event
        send_meta_capi_event(
            event_name="Subscribe",
            user_email=user.email,
            value=float(billing.amount),
            currency=billing.currency or "USD",
            event_id=f"subscribe_{billing.id}",
            custom_data={
                "content_type": "product",
                "content_name": "iMVIO Pro Monthly Subscription",
                "content_category": "subscription"
            }
        )
    except Exception:
        logger.exception("capi_subscription_renewal_failed", extra={"billing_id": billing_history_id})


def submit_order_to_gelato(order_id):
    with transaction.atomic():
        order = PrintOrder.objects.select_for_update().get(id=order_id)
        if order.status == PrintOrder.Status.SENT_TO_GELATO and order.gelato_order_id:
            return

    try:
        response = GelatoService.submit_order(order)
        order.gelato_order_id = response.get("id", "")
        order.gelato_error_message = ""
        order.status = PrintOrder.Status.SENT_TO_GELATO
        order.save(update_fields=["gelato_order_id", "gelato_error_message", "status", "updated_at"])
    except Exception as exc:
        # Payment is already completed; keep status as PAID and allow retry.
        logger.exception("gelato_submission_failed", extra={"order_id": order.id, "error_message": str(exc)})
        order.gelato_error_message = str(exc)
        if order.status != PrintOrder.Status.PAID:
            order.status = PrintOrder.Status.PAID
        order.save(update_fields=["status", "gelato_error_message", "updated_at"])
        return


def process_order_paid(order_id):
    with transaction.atomic():
        order = PrintOrder.objects.select_for_update().get(id=order_id)
        if order.status in [PrintOrder.Status.PAID, PrintOrder.Status.SENT_TO_GELATO]:
            return

        order.status = PrintOrder.Status.PAID
        order.save(update_fields=["status", "updated_at"])

    # Send order confirmation email (outside atomic block)
    try:
        user = User.all_objects.get(id=order.user_id)
        send_order_confirmed_email(user=user, order=order)
    except Exception:
        logger.exception("order_email_failed", extra={"order_id": order_id})

    # Send Meta CAPI event (outside atomic block)
    try:
        from apps.core.services.meta_pixel_service import send_meta_capi_event
        send_meta_capi_event(
            event_name="Purchase",
            user_email=user.email,
            value=float(order.amount),
            currency="USD",
            event_id=f"order_{order.id}",
            custom_data={
                "content_type": "product",
                "content_name": f"Print Order #{order.id}",
                "content_category": "print_order"
            }
        )
    except Exception:
        logger.exception("capi_order_paid_failed", extra={"order_id": order_id})

    submit_order_to_gelato(order.id)
