import hashlib
import json
import logging
import threading
import time
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def hash_sha256(value):
    """Hash a string value with SHA-256 for Meta privacy requirements."""
    if not value:
        return ""
    # Ensure it's a string, strip white spaces, and convert to lowercase
    clean_val = str(value).strip().lower()
    return hashlib.sha256(clean_val.encode("utf-8")).hexdigest()

def send_meta_capi_event(event_name, user_email, value=None, currency="USD", request=None, fbc=None, fbp=None, custom_data=None, event_id=None):
    """
    Asynchronously fires a Meta Conversions API (CAPI) event from the server.
    Ensures that external HTTP latency does not block Django requests.
    """
    pixel_id = getattr(settings, "META_PIXEL_ID", "")
    access_token = getattr(settings, "META_ACCESS_TOKEN", "")

    if not pixel_id or not access_token:
        logger.warning("Meta Pixel ID or Access Token is not configured. Skipping Meta CAPI event.")
        return

    # Extract user IP, User Agent, and Meta cookies if a request object is present
    client_ip = None
    client_user_agent = None

    if request:
        # Extract IP (respecting reverse proxies)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.META.get("REMOTE_ADDR")

        # Extract User Agent
        client_user_agent = request.META.get("HTTP_USER_AGENT")

        # Extract fbc / fbp cookies from request
        if not fbc:
            fbc = request.COOKIES.get("_fbc")
            if not fbc and hasattr(request, "data") and isinstance(request.data, dict):
                fbc = request.data.get("fbc") or request.data.get("_fbc")
            if not fbc and hasattr(request, "query_params"):
                fbc = request.query_params.get("fbc") or request.query_params.get("_fbc")

        if not fbp:
            fbp = request.COOKIES.get("_fbp")
            if not fbp and hasattr(request, "data") and isinstance(request.data, dict):
                fbp = request.data.get("fbp") or request.data.get("_fbp")
            if not fbp and hasattr(request, "query_params"):
                fbp = request.query_params.get("fbp") or request.query_params.get("_fbp")

    # Spawn thread to perform Graph API call asynchronously
    thread = threading.Thread(
        target=_execute_capi_post,
        args=(pixel_id, access_token, event_name, user_email, value, currency, client_ip, client_user_agent, fbc, fbp, custom_data, event_id),
        name=f"meta-capi-{event_name}"
    )
    thread.daemon = True
    thread.start()

def _execute_capi_post(pixel_id, access_token, event_name, user_email, value, currency, client_ip, client_user_agent, fbc, fbp, custom_data, event_id):
    url = f"https://graph.facebook.com/v19.0/{pixel_id}/events"

    user_data = {}
    if user_email:
        user_data["em"] = [hash_sha256(user_email)]
    if client_ip:
        user_data["client_ip_address"] = client_ip
    if client_user_agent:
        user_data["client_user_agent"] = client_user_agent
    if fbc:
        user_data["fbc"] = fbc
    if fbp:
        user_data["fbp"] = fbp

    # Construct CAPI Event object
    event = {
        "event_name": event_name,
        "event_time": int(time.time()),
        "action_source": "website" if client_ip else "system_generated",
        "user_data": user_data,
    }

    if event_id:
        event["event_id"] = str(event_id)

    # Build custom data block (value, currency, custom properties)
    cd = {}
    if value is not None:
        try:
            cd["value"] = float(value)
        except (ValueError, TypeError):
            pass
    if currency:
        cd["currency"] = str(currency).upper()

    if custom_data and isinstance(custom_data, dict):
        cd.update(custom_data)

    if cd:
        event["custom_data"] = cd

    payload = {
        "data": [event],
        "access_token": access_token
    }

    log_file_path = "meta_pixel_debug.log"
    try:
        # Write debug details before sending
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- [CAPI Trigger] Event: {event_name} for {user_email or 'unknown'} ---\n")
            f.write(f"Payload: {json.dumps(event, indent=2)}\n")

        response = requests.post(url, json=payload, timeout=10)
        
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"Response Status: {response.status_code}\n")
            f.write(f"Response Body: {response.text}\n")
            f.write(f"--- [CAPI End] ---\n")

        if response.status_code != 200:
            logger.error(f"Meta CAPI event '{event_name}' failed with status {response.status_code}: {response.text}")
        else:
            logger.info(f"Meta CAPI event '{event_name}' sent successfully.")

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"--- [CAPI Error] Error: {str(e)}\nTraceback:\n{tb}\n")
        logger.exception("Failed to send Meta CAPI event")
