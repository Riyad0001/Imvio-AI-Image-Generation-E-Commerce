import requests
from django.conf import settings

from apps.image_gen.models import GeneratedImage


class GelatoService:
    @staticmethod
    def _build_shipping_address(order):
        address = order.shipping_address or {}
        
        # Parse full name into first and last name
        full_name = str(address.get("name", "")).strip()
        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Extract and validate required fields
        address_line1 = str(address.get("address_line1", "")).strip()
        city = str(address.get("city", "")).strip()
        country = str(address.get("country", "")).strip().upper()  # Ensure uppercase country code
        postal_code = str(address.get("postal_code", "")).strip()
        
        print(f"[GELATO ADDRESS DEBUG] name: {full_name}")
        print(f"[GELATO ADDRESS DEBUG] first_name: {first_name}, last_name: {last_name}")
        print(f"[GELATO ADDRESS DEBUG] address_line1: {address_line1}")
        print(f"[GELATO ADDRESS DEBUG] city: {city}")
        print(f"[GELATO ADDRESS DEBUG] country: {country}")
        print(f"[GELATO ADDRESS DEBUG] postal_code raw: '{address.get('postal_code')}' -> processed: '{postal_code}'")
        
        # Validate all required fields are not empty
        if not all([first_name, last_name, address_line1, city, country, postal_code]):
            missing = []
            if not first_name: missing.append("first_name")
            if not last_name: missing.append("last_name")
            if not address_line1: missing.append("address_line1")
            if not city: missing.append("city")
            if not country: missing.append("country")
            if not postal_code: missing.append("postal_code")
            error_msg = f"Missing required shipping fields: {', '.join(missing)}"
            print(f"[GELATO ADDRESS ERROR] {error_msg}")
            raise ValueError(error_msg)

        # Build required address object
        shipping_address = {
            "firstName": first_name,
            "lastName": last_name,
            "addressLine1": address_line1,
            "city": city,
            "postCode": postal_code,  # Note: Gelato expects "postCode" with capital C
            "country": country,
        }

        # Add optional fields only if they have values
        email = str(address.get("email", "")).strip()
        if email:
            shipping_address["email"] = email

        phone = str(address.get("phone", "")).strip()
        if phone:
            shipping_address["phone"] = phone

        address_line2 = str(address.get("address_line2", "")).strip()
        if address_line2:
            shipping_address["addressLine2"] = address_line2

        state = str(address.get("state", "")).strip()
        if state:
            shipping_address["state"] = state

        print(f"[GELATO ADDRESS DEBUG] Final shipping_address: {shipping_address}")
        return shipping_address

    @staticmethod
    def submit_order(order):
        try:
            print(f"\n[GELATO] ===== Starting order submission for PrintOrder#{order.id} =====")
            
            image = GeneratedImage.objects.filter(id=order.generated_image_id, is_deleted=False).first()
            if not image or not image.image:
                raise ValueError("Generated image file not found for this order")

            # Gelato must fetch a publicly reachable file URL.
            image_url = f"{settings.BACKEND_BASE_URL}{image.image.url}"
            print(f"[GELATO] Image URL: {image_url}")

            headers = {
                "X-API-KEY": settings.GELATO_API_KEY,
                "Content-Type": "application/json",
            }

            # Build item options - only include non-None values (size is in product_type)
            item_options = {}

            print(f"[GELATO] Product type: {order.product_type}")
            print(f"[GELATO] Item options: {item_options}")

            # Build shipping address
            shipping_address = GelatoService._build_shipping_address(order)

            payload = {
                "orderReferenceId": f"print-order-{order.id}",
                "currency": "USD",
                "shippingAddress": shipping_address,
                "items": [
                    {
                        "itemReferenceId": f"item-{order.id}",
                        "productUid": order.product_type,
                        "quantity": 1,
                        "options": item_options,
                        "files": [
                            {
                                "type": "default",
                                "url": image_url,
                            }
                        ],
                    }
                ],
                "metadata": {
                    "generated_image_id": order.generated_image_id,
                    "product_size_id": order.product_size.id,
                },
            }

            print(f"[GELATO] Full payload being sent:")
            import json
            print(json.dumps(payload, indent=2))

            print(f"[GELATO] Sending POST request to {settings.GELATO_BASE_URL}/orders")
            response = requests.post(f"{settings.GELATO_BASE_URL}/orders", headers=headers, json=payload, timeout=60)
            
            print(f"[GELATO] Response status: {response.status_code}")
            print(f"[GELATO] Response headers: {response.headers}")
            print(f"[GELATO] Response body: {response.text}")

            if response.status_code not in (200, 201, 202):
                error_msg = f"Gelato API returned {response.status_code}: {response.text}"
                print(f"[GELATO ERROR] {error_msg}")
                raise ValueError(error_msg)
            
            response_data = response.json()
            print(f"[GELATO] Order submitted successfully. Response: {response_data}")
            print(f"[GELATO] ===== Order submission complete for PrintOrder#{order.id} =====\n")
            
            return response_data
        except Exception as exc:
            print(f"[GELATO ERROR] Exception during submit_order: {str(exc)}")
            print(f"[GELATO ERROR] ===== Order submission failed for PrintOrder#{order.id} =====\n")
            raise
