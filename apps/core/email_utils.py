"""
Shared email sending utility for iMVIO.
All transactional emails should go through these helpers.
Emails are sent in background threads so they NEVER block API responses.
"""
import threading
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)


def _do_send(subject, template_name, context, to_email):
    """Render template and send — runs inside a background thread."""
    log_file_path = "mail_debug.log"
    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- [Thread Start] Sending to {to_email} with template {template_name} ---\n")
        
        html_body = render_to_string(f"emails/{template_name}", context)
        plain_body = subject

        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send()
        
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"--- [Thread Success] Email sent successfully to {to_email} ---\n")
        logger.info("email_sent", extra={"template": template_name, "to": to_email})
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"--- [Thread Error] Failed sending to {to_email}. Error: {str(e)}\nTraceback:\n{tb}\n")
        logger.exception("email_send_failed", extra={"template": template_name, "to": to_email})


def _send_html_email(subject, template_name, context, to_email):
    """
    Fire-and-forget email in a background thread.
    The API response is returned to the user immediately.
    """
    t = threading.Thread(
        target=_do_send,
        args=(subject, template_name, context, to_email),
    )
    t.start()




def send_welcome_email(user, credits=0):
    _send_html_email(
        subject="Welcome to iMVIO – Let's get creative! 🎨",
        template_name="welcome_email.html",
        context={
            "full_name": user.full_name or user.email.split("@")[0],
            "credits": credits,
        },
        to_email=user.email,
    )




def send_otp_email(email, otp):
    _send_html_email(
        subject="Your iMVIO Verification Code",
        template_name="otp_email.html",
        context={"otp": otp},
        to_email=email,
    )


def send_subscription_activated_email(user, credits=300, plan_name="iMVIO Pro", billing_interval="Monthly"):
    _send_html_email(
        subject="🎉 Your iMVIO Subscription is Active!",
        template_name="subscription_activated_email.html",
        context={
            "full_name": user.full_name or user.email.split("@")[0],
            "plan_name": plan_name,
            "credits": credits,
            "billing_interval": billing_interval,
        },
        to_email=user.email,
    )


def send_credits_purchased_email(user, credits, amount, total_balance):
    _send_html_email(
        subject=f"⚡ {credits} Credits Added to Your iMVIO Account",
        template_name="credits_purchased_email.html",
        context={
            "full_name": user.full_name or user.email.split("@")[0],
            "credits": credits,
            "amount": f"{amount:.2f}",
            "total_balance": total_balance,
        },
        to_email=user.email,
    )


def send_order_confirmed_email(user, order):
    shipping = order.shipping_address or {}
    _send_html_email(
        subject=f"🖨️ Your iMVIO Print Order #{order.id} is Confirmed",
        template_name="order_confirmed_email.html",
        context={
            "full_name": user.full_name or user.email.split("@")[0],
            "order_id": order.id,
            "product_name": getattr(order, "product_type", None) or "Wall Art Print",
            "size": getattr(order, "size", None) or "",
            "amount": f"{order.amount:.2f}",
            "shipping_name": shipping.get("name", user.full_name or ""),
            "shipping_address": ", ".join(filter(None, [
                shipping.get("address_line1", ""),
                shipping.get("city", ""),
                shipping.get("state", ""),
                shipping.get("country", ""),
            ])),
        },
        to_email=user.email,
    )
