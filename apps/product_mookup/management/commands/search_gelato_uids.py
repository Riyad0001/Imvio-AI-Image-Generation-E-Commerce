from django.core.management.base import BaseCommand
from django.conf import settings
import requests

class Command(BaseCommand):
    help = "Search Gelato product UIDs by catalog name and size"

    def add_arguments(self, parser):
        parser.add_argument("catalog", type=str, help="Catalog keyword or UID (e.g., acrylic, canvas, posters, framed-posters)")
        parser.add_argument("--size", type=str, help="Optional size filter (e.g., 12x16, 12x12, 30x40)")
        parser.add_argument("--orientation", type=str, choices=["ver", "hor", "sq"], help="Optional orientation filter (ver, hor, sq)")

    def handle(self, *args, **options):
        catalog_query = options["catalog"].lower()
        size_filter = options.get("size")
        orientation_filter = options.get("orientation")

        if not settings.GELATO_API_KEY:
            self.stderr.write("Error: GELATO_API_KEY is not configured in settings.")
            return

        headers = {
            "X-API-KEY": settings.GELATO_API_KEY,
            "Content-Type": "application/json"
        }

        # 1. Fetch available catalogs to find the closest match
        self.stdout.write("Fetching catalogs from Gelato...")
        response = requests.get("https://product.gelatoapis.com/v3/catalogs", headers=headers)
        if response.status_code != 200:
            self.stderr.write(f"Error fetching catalogs: {response.text}")
            return

        catalogs = response.json().get("data", [])
        matched_catalog = None
        for cat in catalogs:
            uid = cat.get("catalogUid", "").lower()
            title = cat.get("title", "").lower()
            if catalog_query == uid or catalog_query in uid or catalog_query in title:
                matched_catalog = cat
                break

        if not matched_catalog:
            self.stderr.write(f"No catalog found matching: {options['catalog']}")
            self.stdout.write("Available catalogs:")
            for cat in catalogs:
                self.stdout.write(f"  - {cat.get('catalogUid')} ({cat.get('title')})")
            return

        catalog_uid = matched_catalog.get("catalogUid")
        self.stdout.write(self.style.SUCCESS(f"Searching in catalog: {catalog_uid} ({matched_catalog.get('title')})"))

        # 2. Search products in that catalog
        products = []
        limit = 100
        offset = 0

        self.stdout.write("Fetching product UIDs...")
        while True:
            payload = {
                "limit": limit,
                "offset": offset
            }
            search_url = f"https://product.gelatoapis.com/v3/catalogs/{catalog_uid}/products:search"
            res = requests.post(search_url, headers=headers, json=payload)
            if res.status_code != 200:
                self.stderr.write(f"Error searching products: {res.text}")
                return

            res_data = res.json()
            page_products = res_data.get("products", [])
            products.extend(page_products)

            if len(page_products) < limit:
                break
            offset += limit

        self.stdout.write(f"Total products found in catalog: {len(products)}")

        # 3. Filter and display
        filtered_products = []
        for p in products:
            uid = p.get("productUid", "")
            
            # Filter by size if provided
            if size_filter:
                # E.g. match "12x16" in "acrylic_12x16-inch-300x400-mm_4-mm_4-0_ver"
                # Check for standard display size format (e.g. 12x16) or mm size format (e.g. 300x400)
                clean_size = size_filter.replace(" ", "").lower()
                if clean_size not in uid.lower():
                    continue

            # Filter by orientation if provided
            if orientation_filter:
                if orientation_filter == "ver" and not uid.endswith("_ver"):
                    continue
                if orientation_filter == "hor" and not uid.endswith("_hor"):
                    continue
                if orientation_filter == "sq" and not uid.endswith("_sq"):
                    continue

            filtered_products.append(p)

        if not filtered_products:
            self.stdout.write(self.style.WARNING("No products matched your filters."))
            return

        self.stdout.write(self.style.SUCCESS(f"\nMatching Gelato UIDs ({len(filtered_products)} results):"))
        self.stdout.write(f"{'Gelato Product UID':<70} | {'Name/Description'}")
        self.stdout.write("-" * 100)
        for p in filtered_products[:50]:
            name = p.get("name") or "N/A"
            self.stdout.write(f"{p.get('productUid'):<70} | {name}")

        if len(filtered_products) > 50:
            self.stdout.write(self.style.WARNING(f"\nShowing first 50 results. Narrow down search using --size or --orientation options."))
