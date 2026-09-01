import stripe
from django.conf import settings


stripe.api_key = settings.STRIPE_SECRET_KEY


CREDIT_PACKAGES = {
    "40": {"amount": 40, "credits": 200, "price_id": settings.STRIPE_CREDIT_PRICE_40},
    "50": {"amount": 50, "credits": 300, "price_id": settings.STRIPE_CREDIT_PRICE_50},
    "60": {"amount": 60, "credits": 350, "price_id": settings.STRIPE_CREDIT_PRICE_60},
}


class StripeService:
    @staticmethod
    def create_checkout_session(*, user, mode, success_path, cancel_path, line_items, metadata=None, client_reference_id=None):
        session = stripe.checkout.Session.create(
            customer_email=user.email,
            line_items=line_items,
            mode=mode,
            success_url="http://imvio.com.au/success/?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://imvio.com.au/cancel/",
            metadata=metadata or {},
            client_reference_id=client_reference_id,
            allow_promotion_codes=True,
        )
        return session
