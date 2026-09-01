import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

# PRICE_LOOKUP = {
#     ("package-1", "monthly"): "price_1RoY9VRfX6BK6Cwps0rAdYAc",
#     ("package-1", "yearly"): "price_1RoYAfRfX6BK6CwpvoVvynJt",
#     ("package-2", "monthly"): "price_1RoYC2RfX6BK6CwpO51ZAqOO",
#     ("package-2", "yearly"): "price_1RoYDARfX6BK6CwpAGo7t0yB",
# }

# clients real payment packages 
# PRICE_LOOKUP = {
#     ("package-1", "monthly"): "price_1RrkFc5izR1x5g2e1F2RTDBG",
#     ("package-1", "yearly"): "price_1RrkH25izR1x5g2ePuDGeeEc",
#     ("package-2", "monthly"): "price_1RrkKF5izR1x5g2eDphYedWD",
#     ("package-2", "yearly"): "price_1RrkLo5izR1x5g2eGfs6QAjB",
# }
# clients test payment packages 
PRICE_LOOKUP = {
    ("package-1", "monthly"): "price_1RheYDRfX6BK6CwpDOUj26AG"
}

def create_checkout_session(user, package, billing):
    price_id = PRICE_LOOKUP[(package, billing)]
    package_number = 1 if package == "package-1" else 2
    customer = stripe.Customer.create(email=user.email)
    session = stripe.checkout.Session.create(
        customer=customer.id,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url="http://imvio.com.au/success/?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="http://imvio.com.au/cancel/",
        allow_promotion_codes=True,
    )
    return session.url