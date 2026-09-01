from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import make_aware
from .models import Subscription
from .services.payment_service import PaymentService
from .services.exceptions import ServiceError
import stripe, datetime
from django.conf import settings
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import stripe, json
import logging
from .models import Subscription
from django.utils.timezone import make_aware
from datetime import datetime
from rest_framework.exceptions import NotFound
from django.contrib.auth import get_user_model
User = get_user_model()
logger = logging.getLogger(__name__)
# PRICE_LOOKUP = {
#     ("package-1", "monthly"): "price_1RoY9VRfX6BK6Cwps0rAdYAc",
#     ("package-1", "yearly"): "price_1RoYAfRfX6BK6CwpvoVvynJt",
#     ("package-2", "monthly"): "price_1RoYC2RfX6BK6CwpO51ZAqOO",
#     ("package-2", "yearly"): "price_1RoYDARfX6BK6CwpAGo7t0yB",
# }

# client real payment packages
# PRICE_LOOKUP = {
#     ("package-1", "monthly"): "price_1RrkFc5izR1x5g2e1F2RTDBG",
#     ("package-1", "yearly"): "price_1RrkH25izR1x5g2ePuDGeeEc",
#     ("package-2", "monthly"): "price_1RrkKF5izR1x5g2eDphYedWD",
#     ("package-2", "yearly"): "price_1RrkLo5izR1x5g2eGfs6QAjB",
# }
# client test payment packages


PRICE_LOOKUP = {
    ("package-1", "monthly"): "price_1RheYDRfX6BK6CwpDOUj26AG"
}

stripe.api_key = settings.STRIPE_SECRET_KEY



class BaseAPIView(APIView):
    def success_response(self, message="Your request Accepted", data=None, status_code= status.HTTP_200_OK):
        return Response(
            {
            "success": True,
            "message": message,
            "status": status_code,
            "data": data or {}
            },
            status=status_code )
    def error_response(self, message="Your request rejected", data=None, status_code= status.HTTP_400_BAD_REQUEST):
        return Response(
            {
            "success": False,
            "message": message,
            "status": status_code,
            "data": data or {}
            },
            status=status_code ) 


#  User payment checkout url give in stripe redirection    
class CreateCheckoutView(BaseAPIView):  # Inherit from BaseAPIView
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            checkout_url = PaymentService.create_subscription_checkout(user=request.user, request=request)
            return self.success_response(
                message="Checkout session created successfully",
                data={"checkout_url": checkout_url},
                status_code=status.HTTP_200_OK
            )
        except ServiceError as exc:
            return self.error_response(
                message=exc.message,
                status_code=exc.status_code
            )
        except Exception as e:
            return self.error_response(
                message=f"Checkout failed: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# user Subscription plan cancellation - CANCEL ONLY
class CancelSubscriptionView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return self.error_response("No active subscription found for this user.", status_code=404)

        # Return cancel status for toggle button
        cancel_enabled = not sub.auto_renew
        return self.success_response("Cancel subscription status retrieved.", data={"cancel_enabled": cancel_enabled})

    def post(self, request):
        try:
            sub = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return self.error_response("No active subscription found for this user.", status_code=404)

        if not sub.stripe_subscription_id:
            sub.is_active = False
            sub.auto_renew = False
            sub.save(update_fields=["is_active", "auto_renew"])
            return self.error_response("No active Stripe subscription found.", status_code=404)

        try:
            stripe.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=True
            )
            sub.auto_renew = False
            sub.save()
        except stripe.error.InvalidRequestError:
            # Stripe subscription was deleted or never existed in this account.
            sub.is_active = False
            sub.auto_renew = False
            sub.stripe_subscription_id = ""
            sub.save(update_fields=["is_active", "auto_renew", "stripe_subscription_id"])
            return self.error_response("No active Stripe subscription found.", status_code=404)
        except stripe.error.StripeError as e:
            return self.error_response("Stripe error: " + str(e), status_code=400)

        return self.success_response("Subscription cancellation scheduled at period end.", data={"cancel_enabled": True})


# Auto renew subscription - dedicated endpoint for AUTO-RENEWAL
class AutoRenewSubscriptionView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return self.error_response("No active subscription found for this user.", status_code=404)

        # Return auto-renew status for toggle button
        return self.success_response("Auto-renew subscription status retrieved.", data={"auto_renew": sub.auto_renew})

    def post(self, request):
        try:
            sub = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return self.error_response("No active subscription found for this user.", status_code=404)

        if not sub.stripe_subscription_id:
            sub.is_active = False
            sub.auto_renew = False
            sub.save(update_fields=["is_active", "auto_renew"])
            return self.error_response("No active Stripe subscription found.", status_code=404)

        try:
            stripe.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=False
            )
            sub.auto_renew = True
            sub.save()
        except stripe.error.InvalidRequestError:
            # Stripe subscription was deleted or never existed in this account.
            sub.is_active = False
            sub.auto_renew = False
            sub.stripe_subscription_id = ""
            sub.save(update_fields=["is_active", "auto_renew", "stripe_subscription_id"])
            return self.error_response("No active Stripe subscription found.", status_code=404)
        except stripe.error.StripeError as e:
            return self.error_response("Stripe error: " + str(e), status_code=400)

        return self.success_response("Subscription auto-renewal enabled successfully.", data={"auto_renew": True})


# user Subscription plan upgrade which only monthly subscription can be upgraded yearly
class UpgradeSubscriptionView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        new_package = request.data.get("package")
        new_billing = request.data.get("billing")

        if not new_package or not new_billing:
            return self.error_response("Package and billing are required.", status_code=400)

        try:
            sub = Subscription.objects.get(user=user)
        except Subscription.DoesNotExist:
            return self.error_response("No active subscription found.", status_code=404)

        if sub.billing_interval != "month":
            return self.error_response("Only monthly subscriptions can be upgraded.", status_code=400)

        current_package = sub.package
        new_price_id = PRICE_LOOKUP.get((new_package, new_billing))

        if not new_price_id:
            return self.error_response("Invalid package or billing option.", status_code=400)

        if new_package == current_package and new_billing == sub.billing_interval:
            return self.error_response("Already subscribed to this package.", status_code=400)

        try:
            stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
            item_id = stripe_sub["items"]["data"][0]["id"]

            if stripe_sub.get("cancel_at_period_end"):
                stripe.Subscription.modify(
                    sub.stripe_subscription_id,
                    cancel_at_period_end=False
                )

            stripe.Subscription.modify(
                sub.stripe_subscription_id,
                items=[{
                    "id": item_id,
                    "price": new_price_id
                }],
                proration_behavior="create_prorations",
            )

            sub.package = new_package
            sub.billing_interval = new_billing
            sub.auto_renew = True
            sub.save()

            return self.success_response("Subscription upgraded successfully.")

        except Exception as e:
            return self.error_response(str(e), status_code=500)


# user Subscription status and details
class MySubscriptionView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return self.error_response("No active subscription found for this user.", status_code=status.HTTP_200_OK)

        if (sub.current_period_start is None or sub.current_period_end is None) and sub.stripe_subscription_id:
            try:
                sub = PaymentService.sync_subscription_periods(sub)
            except Exception:
                logger.exception("subscription_period_sync_failed", extra={"subscription_id": sub.stripe_subscription_id})

        data = {
            "package": sub.package,
            "billing_interval": sub.billing_interval,
            "auto_renew": sub.auto_renew,
            "current_period_end": sub.current_period_end,
            "current_period_start": sub.current_period_start,
        }

        return self.success_response("Subscription data retrieved successfully.", data)

# All payment and payment history 
class InvoiceHistoryView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            try:
                sub = Subscription.objects.select_related('user').get(user=request.user)
            except Subscription.DoesNotExist:
                return self.error_response(
                    message="No subscription found for this user",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            try:
                invoices = stripe.Invoice.list(customer=sub.stripe_customer_id, limit=100)

                invoice_data = [
                    {
                        "invoice_id": inv["id"],
                        "number": inv["number"],
                        "amount_paid": inv["amount_paid"] / 100,
                        "created": make_aware(datetime.fromtimestamp(inv["created"])).isoformat(),
                        "status": inv["status"],
                        "invoice_pdf": inv["invoice_pdf"],
                        "description": inv.get("description", None),
                    }
                    for inv in invoices["data"]
                ]

                return self.success_response(
                    message="Invoice history retrieved successfully",
                    data={"invoices": invoice_data}
                )

            except stripe.error.StripeError as e:
                return self.error_response(
                    message=f"Stripe API error: {str(e)}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return self.error_response(
                message="An unexpected error occurred",
                data={"error": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Card Save Features
# class SaveCardView(BaseAPIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         payment_method_id = request.data.get("payment_method_id")
#         if not payment_method_id:
#             return self.error_response("Payment method ID is required", status_code=400)

#         try:
#             sub = Subscription.objects.get(user=request.user)
#             customer_id = sub.stripe_customer_id

#             # Attach to customer
#             stripe.PaymentMethod.attach(
#                 payment_method_id,
#                 customer=customer_id
#             )

#             # Optionally set as default
#             stripe.Customer.modify(
#                 customer_id,
#                 invoice_settings={
#                     'default_payment_method': payment_method_id,
#                 }
#             )

#             return self.success_response("Card saved successfully.")

#         except Exception as e:
#             return self.error_response(str(e), status_code=500)


class ListSavedCardsView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub = Subscription.objects.get(user=request.user)
            customer_id = sub.stripe_customer_id

            cards = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )

            data = [
                {
                    "id": card.id,
                    "brand": card.card.brand,
                    "last4": card.card.last4,
                    "exp_month": card.card.exp_month,
                    "exp_year": card.card.exp_year,
                    "is_default": (card.id == stripe.Customer.retrieve(customer_id).invoice_settings.default_payment_method)
                }
                for card in cards.data
            ]

            return self.success_response("Saved cards retrieved.", data=data)

        except Exception as e:
            return self.error_response(str(e), status_code=500)



class StripePaymentSuccessView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return self.success_response(message="Payment completed successfully.")

# Stripe Webhook to handle events like subscription creation,cancellation,and invoice creation
@csrf_exempt
def stripe_webhook(request):
    print("🔔 Stripe Webhook triggered")

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if sig_header is None:
        return JsonResponse({'error': 'missing signature header'}, status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        print(f" Stripe event received: {event['type']}")
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'invalid signature'}, status=400)
    except Exception as e:
        print(f" Exception during event parsing: {e}")
        return JsonResponse({'error': str(e)}, status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        email = session.get("customer_email") or session.get("customer_details", {}).get("email")

        if not email:
            return JsonResponse({"error": "No customer email found in session"}, status=400)

        user = User.objects.filter(email=email).first()
        if not user:
            return JsonResponse({"error": f"No user found with email {email}"}, status=404)

        print(f" Matched user: {user.email}")

        try:
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
            print(" Stripe Subscription:", stripe_sub)

            item_data = stripe_sub.get("items", {}).get("data", [])
            if item_data:
                item = item_data[0]  # First subscription item
                period_start_ts = item.get("current_period_start")  # Access from item, not stripe_sub
                period_end_ts = item.get("current_period_end")
                price_id = item["price"]["id"]
                price = item.get("price", {})
                price_id = price.get("id")
                recurring = price.get("recurring", {})
                interval = recurring.get("interval")
                print("Interval:", interval)
                package = get_package_from_price_id(price_id)
            else:
                item = {}
                package = "unknown"
                interval = None
                period_start_ts = period_end_ts = None

            Subscription.objects.update_or_create(
                user=user,
                defaults={
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                    "package": package,
                    "billing_interval": interval,
                    "current_period_start": make_aware(datetime.fromtimestamp(period_start_ts)) if period_start_ts else None,
                    "current_period_end": make_aware(datetime.fromtimestamp(period_end_ts)) if period_end_ts else None,
                    "auto_renew": not stripe_sub.get("cancel_at_period_end", False),
                    "is_active": True
                }
            )
            print(" Subscription updated/created")

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif event["type"] == "customer.subscription.deleted":
        print(" Handling customer.subscription.deleted")
        stripe_sub = event["data"]["object"]
        sub = Subscription.objects.filter(stripe_subscription_id=stripe_sub["id"]).first()
        if sub:
            sub.is_active = False
            sub.save()
            print(f" Subscription {sub.id} marked inactive")

    elif event["type"] == "invoice.created":
        invoice = event["data"]["object"]
        print(f"🧾 Invoice created: {invoice['id']}")
        return JsonResponse({'status': 'invoice.created received'}, status=200)

    return JsonResponse({"status": "ok"})

# 🔍 Debugging for package ID resolution
def get_package_from_price_id(price_id):
    print(f" Looking up package for price_id: {price_id}")
    for (pkg, billing), pid in PRICE_LOOKUP.items():
        if pid == price_id:
            print(f"✅ Matched package: {pkg} with billing {billing}")
            return pkg
    print(" No package match found")
    return "unknown"







# permission classes 
from rest_framework.permissions import BasePermission
class HasPackage1Subscription(BasePermission):
    def has_permission(self, request, view):
        try:
            sub = Subscription.objects.get(user=request.user)
            return (
                sub.package == "package-1" and
                sub.is_active
            )
        except Subscription.DoesNotExist:
            return False
        
class HasPackage2Subscription(BasePermission):
    def has_permission(self, request, view):
        try:
            sub = Subscription.objects.get(user=request.user)
            return (
                sub.package == "package-2" and
                sub.is_active
            )
        except Subscription.DoesNotExist:
            return False
    

import stripe
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeSessionDetailsAPIView(APIView):

    def get(self, request):
        session_id = request.query_params.get("session_id")

        if not session_id:
            return Response(
                {"error": "session_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = stripe.checkout.Session.retrieve(session_id)

            line_items = stripe.checkout.Session.list_line_items(session_id)

            return Response({
                "session_id": session.id,
                "customer_id": session.customer,
                "payment_status": session.payment_status,
                "amount_total": session.amount_total / 100,
                "currency": session.currency,
                "line_items": [
                    {
                        "description": item.description,
                        "quantity": item.quantity,
                        "amount_total": item.amount_total / 100,
                    }
                    for item in line_items.data
                ]
            })

        except stripe.error.StripeError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )