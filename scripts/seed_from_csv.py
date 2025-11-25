#!/usr/bin/env python3
"""
Seed the Shopifake stack by reading structured CSV data and calling service APIs.

For every CSV row the script:
1. Creates (or reuses) a site via the Sites service.
2. Ensures categories and filters exist in the Catalog service.
3. Creates products with filter assignments.
4. Creates an initial price in the Pricing service.
5. Initializes stock in the Inventory service.

Usage:
    python scripts/seed_from_csv.py --csv data/seed-data.csv

Environment variables / flags:
    --csv / SEED_CSV_PATH            Path to the CSV file.
    --gateway-base-url / GATEWAY_BASE_URL
                                     Gateway URL that proxies every service.
    --owner-id / DEFAULT_OWNER_ID    UUID used for the X-Owner-Id header.

The default gateway URL points to the docker-compose dev port (http://localhost:9000).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import urlencode


LOGGER = logging.getLogger("seed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Shopifake services from CSV.")
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default=os.getenv("SEED_CSV_PATH", "data/seed-data.csv"),
        help="Path to the CSV data file.",
    )
    parser.add_argument(
        "--gateway-base-url",
        dest="gateway_base_url",
        default=os.getenv("GATEWAY_BASE_URL", "http://localhost:9000"),
        help="Base URL for the API gateway (proxies sites, catalog, inventory, pricing).",
    )
    parser.add_argument(
        "--owner-id",
        dest="owner_id",
        default=os.getenv("DEFAULT_OWNER_ID", "11111111-1111-1111-1111-111111111111"),
        help="Owner UUID used when creating sites.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse the CSV and print the intended operations without calling any endpoint.",
    )
    return parser.parse_args()


def load_rows(csv_path: Path) -> List[Dict[str, Any]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for index, raw in enumerate(reader, start=2):
            try:
                rows.append(_normalize_row(raw))
            except Exception as exc:  # pragma: no cover - defensive logging
                raise ValueError(f"Failed to parse CSV row {index}: {exc}") from exc
    return rows


def _normalize_row(raw: Dict[str, str]) -> Dict[str, Any]:
    def parse_json_field(field_name: str) -> Any:
        value = (raw.get(field_name) or "").strip()
        return json.loads(value) if value else None

    filters_payload = parse_json_field("filter_definitions") or []
    product_filters = parse_json_field("product_filters") or {}
    images = [
        item.strip()
        for item in (raw.get("product_images") or "").split("|")
        if item.strip()
    ]
    if not images:
        raise ValueError("product_images must include at least one URL separated by '|'")

    price_amount_raw = (raw.get("price_amount") or "").strip()
    price_amount = float(price_amount_raw) if price_amount_raw else None
    price_currency = (raw.get("price_currency") or "").strip()
    price_effective_from = (raw.get("price_effective_from") or "").strip() or None
    price_effective_to = (raw.get("price_effective_to") or "").strip() or None
    inventory_qty_raw = (raw.get("inventory_initial_quantity") or "").strip()
    inventory_initial_quantity = int(inventory_qty_raw) if inventory_qty_raw else None

    normalized = {
        "site_key": (raw.get("site_key") or "").strip(),
        "site_name": (raw.get("site_name") or "").strip(),
        "site_slug": (raw.get("site_slug") or "").strip(),
        "site_description": (raw.get("site_description") or "").strip(),
        "site_currency": (raw.get("site_currency") or "").strip(),
        "site_language": (raw.get("site_language") or "").strip(),
        "site_config": (raw.get("site_config") or "").strip(),
        "category_name": (raw.get("category_name") or "").strip(),
        "filter_definitions": filters_payload,
        "product_name": (raw.get("product_name") or "").strip(),
        "product_description": (raw.get("product_description") or "").strip(),
        "product_images": images,
        "product_sku": (raw.get("product_sku") or "").strip(),
        "product_status": (raw.get("product_status") or "DRAFT").strip() or "DRAFT",
        "product_scheduled_publish_at": (raw.get("product_scheduled_publish_at") or "").strip() or None,
        "product_filters": product_filters,
        "price_amount": price_amount,
        "price_currency": price_currency,
        "price_effective_from": price_effective_from,
        "price_effective_to": price_effective_to,
        "inventory_initial_quantity": inventory_initial_quantity,
    }

    if normalized["product_status"].upper() == "SCHEDULED" and not normalized["product_scheduled_publish_at"]:
        raise ValueError("product_scheduled_publish_at is required when product_status is SCHEDULED")
    if normalized["price_amount"] is None or not normalized["price_currency"]:
        raise ValueError("price_amount and price_currency are required")
    if normalized["inventory_initial_quantity"] is None:
        raise ValueError("inventory_initial_quantity is required")

    missing = [
        key
        for key, value in normalized.items()
        if value in ("", [])
        and key
        not in (
            "filter_definitions",
            "product_filters",
            "product_scheduled_publish_at",
            "price_effective_from",
            "price_effective_to",
        )
    ]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    return normalized


@dataclass
class CreatedFilter:
    id: str
    key: str
    type: str


@dataclass
class HttpResponse:
    status: int
    body: bytes
    headers: Dict[str, str]

    def json(self) -> Any:
        if not self.body:
            return {}
        return json.loads(self.body.decode("utf-8"))

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class HttpError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


class SimpleHttpClient:
    def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> HttpResponse:
        query = ""
        if params:
            filtered = {key: str(value) for key, value in params.items() if value is not None}
            query_string = urlencode(filtered)
            if query_string:
                query = f"?{query_string}"
        data = None
        req_headers = {"Accept": "application/json"}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        if headers:
            req_headers.update(headers)

        request_obj = urlrequest.Request(
            url + query,
            data=data,
            headers=req_headers,
            method=method,
        )
        try:
            with urlrequest.urlopen(request_obj, timeout=timeout) as response:
                body = response.read()
                return HttpResponse(
                    status=response.getcode(),
                    body=body,
                    headers=dict(response.headers.items()),
                )
        except urlerror.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise HttpError(exc.code, body) from None
        except urlerror.URLError as exc:
            raise RuntimeError(f"Failed to reach {url}: {exc}") from exc

    def get(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> HttpResponse:
        return self.request("GET", url, params=params, headers=headers, timeout=timeout)

    def post(
        self,
        url: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> HttpResponse:
        return self.request("POST", url, json_body=json_body, headers=headers, timeout=timeout)


class Seeder:
    def __init__(
        self,
        *,
        gateway_base_url: str,
        owner_id: uuid.UUID,
        dry_run: bool = False,
    ) -> None:
        self.base_url = gateway_base_url.rstrip("/")
        self.owner_id = owner_id
        self.dry_run = dry_run
        self.http = SimpleHttpClient()
        self.site_cache: Dict[str, Dict[str, Any]] = {}
        self.category_cache: Dict[tuple[str, str], Dict[str, Any]] = {}
        self.filter_cache: Dict[tuple[str, str], CreatedFilter] = {}

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    def process_rows(self, rows: Iterable[Dict[str, Any]]) -> None:
        for row in rows:
            site = self._ensure_site(row)
            category = self._ensure_category(site["id"], row["category_name"], row["filter_definitions"])
            filter_assignments = self._ensure_filters_and_map_assignments(site["id"], category["id"], row)
            product_id = self._create_product(site["id"], category["id"], row, filter_assignments)
            self._create_price(product_id, row)
            self._create_inventory(product_id, row)

    # --- Sites -----------------------------------------------------------------
    def _ensure_site(self, row: Dict[str, Any]) -> Dict[str, Any]:
        cache_key = row["site_key"] or row["site_slug"]
        if cache_key in self.site_cache:
            return self.site_cache[cache_key]

        LOGGER.info("Ensuring site '%s' (%s)", row["site_name"], row["site_slug"])
        site = None
        if not self.dry_run:
            site = self._fetch_site_by_slug(row["site_slug"])
        if site:
            LOGGER.info("Site already exists with ID %s", site["id"])
        else:
            payload = {
                "name": row["site_name"],
                "slug": row["site_slug"],
                "description": row["site_description"],
                "currency": row["site_currency"],
                "language": row["site_language"],
                "config": row["site_config"],
            }
            LOGGER.debug("Creating site payload=%s", payload)
            if self.dry_run:
                site = {"id": f"dry-{cache_key}"}
            else:
                try:
                    response = self.http.post(
                        self._url("/api/sites"),
                        json_body=payload,
                        headers={"X-Owner-Id": str(self.owner_id)},
                        timeout=30,
                    )
                    site = response.json()
                    LOGGER.info("Created site %s (%s)", site["id"], site["slug"])
                except HttpError as err:
                    if err.status == 400 and "slug" in err.body.lower():
                        LOGGER.info("Slug already taken, re-fetching site by slug '%s'", row["site_slug"])
                        site = self._fetch_site_by_slug(row["site_slug"])
                    else:
                        raise

        if not site:
            raise RuntimeError(f"Unable to ensure site '{row['site_name']}'")
        self.site_cache[cache_key] = site
        return site

    def _fetch_site_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.http.get(
                self._url(f"/api/sites/slug/{slug}"),
                timeout=15,
            )
            return response.json()
        except HttpError as err:
            body_lower = err.body.lower()
            if err.status == 404 or (err.status == 400 and "site not found" in body_lower):
                return None
            raise

    # --- Categories ------------------------------------------------------------
    def _ensure_category(
        self,
        site_id: uuid.UUID | str,
        category_name: str,
        filter_definitions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        cache_key = (str(site_id), category_name.lower())
        if cache_key in self.category_cache:
            return self.category_cache[cache_key]

        LOGGER.info("Ensuring category '%s' for site %s", category_name, site_id)
        if not self.dry_run:
            existing = self._fetch_categories(site_id)
            for category in existing:
                key = (str(site_id), category["name"].lower())
                self.category_cache[key] = category
        if cache_key in self.category_cache:
            return self.category_cache[cache_key]

        payload = {"siteId": str(site_id), "name": category_name}
        if self.dry_run:
            category = {"id": f"dry-cat-{category_name}", "name": category_name}
        else:
            response = self.http.post(
                self._url("/api/catalog/products/categories"),
                json_body=payload,
                timeout=30,
            )
            category = response.json()
            LOGGER.info("Created category %s", category["id"])

        self.category_cache[cache_key] = category
        # filters for existing categories might already exist; refresh cache if needed
        if filter_definitions and not self.dry_run:
            self._refresh_filters(site_id)
        return category

    def _fetch_categories(self, site_id: uuid.UUID | str) -> List[Dict[str, Any]]:
        response = self.http.get(
            self._url("/api/catalog/products/categories"),
            params={"siteId": str(site_id)},
            timeout=30,
        )
        return response.json()

    # --- Filters ----------------------------------------------------------------
    def _ensure_filters_and_map_assignments(
        self,
        site_id: uuid.UUID | str,
        category_id: uuid.UUID | str,
        row: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        if not self.dry_run:
            self._refresh_filters(site_id)

        self._ensure_filter_definitions(site_id, category_id, row["filter_definitions"])
        assignments: List[Dict[str, Any]] = []
        for key, value in row["product_filters"].items():
            cache_key = self._filter_cache_key(category_id, key)
            cached_filter = self.filter_cache.get(cache_key)
            if not cached_filter:
                raise RuntimeError(f"No filter '{key}' found for category {category_id}")
            assignment = {"filterId": str(cached_filter.id)}
            if cached_filter.type == "QUANTITATIVE":
                assignment["numericValue"] = float(value)
            else:
                assignment["textValue"] = str(value)
            assignments.append(assignment)
        return assignments

    def _ensure_filter_definitions(
        self,
        site_id: uuid.UUID | str,
        category_id: uuid.UUID | str,
        definitions: List[Dict[str, Any]],
    ) -> None:
        if not definitions:
            return

        for definition in definitions:
            cache_key = self._filter_cache_key(category_id, definition["key"])
            if cache_key in self.filter_cache:
                continue
            if self.dry_run:
                self.filter_cache[cache_key] = CreatedFilter(
                    id=f"dry-filter-{definition['key']}",
                    key=definition["key"],
                    type=definition["type"],
                )
                continue
            payload = {
                "siteId": definition.get("siteId") or str(site_id),
                "categoryId": str(category_id),
                "key": definition["key"],
                "type": definition["type"],
                "displayName": definition.get("displayName"),
                "unit": definition.get("unit"),
                "values": definition.get("values"),
                "minValue": definition.get("minValue"),
                "maxValue": definition.get("maxValue"),
            }
            LOGGER.debug("Creating filter payload=%s", payload)
            response = self.http.post(
                self._url("/api/catalog/filters"),
                json_body=payload,
                timeout=30,
            )
            created = response.json()
            created_filter = CreatedFilter(id=created["id"], key=created["key"], type=created["type"])
            self.filter_cache[cache_key] = created_filter
            LOGGER.info("Created filter %s (%s)", created_filter.id, created_filter.key)

    def _refresh_filters(self, site_id: Optional[uuid.UUID | str]) -> None:
        if site_id is None or self.dry_run:
            return
        response = self.http.get(
            self._url("/api/catalog/filters"),
            params={"siteId": str(site_id)},
            timeout=30,
        )
        for entry in response.json():
            cache_key = self._filter_cache_key(entry["categoryId"], entry["key"])
            self.filter_cache[cache_key] = CreatedFilter(
                id=entry["id"],
                key=entry["key"],
                type=entry["type"],
            )

    @staticmethod
    def _filter_cache_key(category_id: uuid.UUID | str, key: str) -> tuple[str, str]:
        return (str(category_id).lower(), key)

    # --- Products --------------------------------------------------------------
    def _create_product(
        self,
        site_id: uuid.UUID | str,
        category_id: uuid.UUID | str,
        row: Dict[str, Any],
        filter_assignments: List[Dict[str, Any]],
    ) -> str:
        payload = {
            "siteId": str(site_id),
            "name": row["product_name"],
            "description": row["product_description"],
            "images": row["product_images"],
            "categoryIds": [str(category_id)],
            "sku": row["product_sku"],
            "status": row["product_status"],
            "filters": filter_assignments,
        }
        if row.get("product_scheduled_publish_at"):
            payload["scheduledPublishAt"] = row["product_scheduled_publish_at"]
        LOGGER.info("Creating product '%s' for site %s", row["product_name"], site_id)
        if self.dry_run:
            LOGGER.debug("DRY RUN product payload=%s", payload)
            return f"dry-product-{row['product_sku']}"
        response = self.http.post(
            self._url("/api/catalog/products"),
            json_body=payload,
            timeout=30,
        )
        product_id = response.json().get("id")
        LOGGER.info("Created product %s", product_id)
        return str(product_id)

    # --- Pricing ---------------------------------------------------------------
    def _create_price(self, product_id: str, row: Dict[str, Any]) -> None:
        payload = {
            "productId": str(product_id),
            "amount": row["price_amount"],
            "currency": row["price_currency"],
        }
        if row.get("price_effective_from"):
            payload["effectiveFrom"] = row["price_effective_from"]
        if row.get("price_effective_to"):
            payload["effectiveTo"] = row["price_effective_to"]

        LOGGER.info("Creating price for product %s", product_id)
        if self.dry_run:
            LOGGER.debug("DRY RUN price payload=%s", payload)
            return
        response = self.http.post(
            self._url("/api/prices"),
            json_body=payload,
            timeout=30,
        )
        LOGGER.info("Created price %s", response.json().get("id"))

    # --- Inventory -------------------------------------------------------------
    def _create_inventory(self, product_id: str, row: Dict[str, Any]) -> None:
        payload = {
            "productId": str(product_id),
            "initialQuantity": row["inventory_initial_quantity"],
        }
        LOGGER.info("Creating inventory for product %s", product_id)
        if self.dry_run:
            LOGGER.debug("DRY RUN inventory payload=%s", payload)
            return
        response = self.http.post(
            self._url("/api/inventory"),
            json_body=payload,
            timeout=30,
        )
        LOGGER.info("Created inventory row %s", response.json().get("id"))


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)


def main() -> None:
    configure_logging()
    args = parse_args()
    try:
        owner_id = uuid.UUID(args.owner_id)
    except ValueError as exc:
        raise SystemExit(f"Invalid owner UUID: {args.owner_id}") from exc

    csv_path = Path(args.csv_path)
    rows = load_rows(csv_path)
    LOGGER.info("Loaded %d rows from %s", len(rows), csv_path)

    seeder = Seeder(
        gateway_base_url=args.gateway_base_url,
        owner_id=owner_id,
        dry_run=args.dry_run,
    )
    seeder.process_rows(rows)


if __name__ == "__main__":
    try:
        main()
    except HttpError as err:
        LOGGER.error("HTTP error %s: %s", err.status, err.body)
        sys.exit(1)
    except Exception as exc:
        LOGGER.error("Seeder failed: %s", exc)
        sys.exit(1)

