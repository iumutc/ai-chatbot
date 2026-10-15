import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from app.rag.ingest import build_index


@dataclass
class EntegraSyncResult:
    products_fetched: int
    products_upserted: int
    index_chunks_written: int
    synced_at: str


class EntegraSyncService:
    def __init__(
        self,
        *,
        enabled: bool,
        base_url: str,
        products_endpoint: str,
        stock_endpoint: str,
        timeout_sec: int,
        auth_type: str,
        token: str,
        api_key: str,
        api_secret: str,
        api_key_header: str,
        api_secret_header: str,
        kb_path: str,
        index_path: str,
        stock_cache_path: str,
        username: str = "",
        password: str = "",
        auth_endpoint: str = "/api/user/token/obtain/",
        max_pages: int = 50,
    ):
        self.enabled = enabled
        self.base_url = base_url.rstrip("/")
        self.products_endpoint = products_endpoint
        self.stock_endpoint = stock_endpoint
        self.timeout_sec = timeout_sec
        self.max_pages = max_pages

        self.auth_type = auth_type.lower()
        self.token = token
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_key_header = api_key_header
        self.api_secret_header = api_secret_header
        self.username = username
        self.password = password
        self.auth_endpoint = auth_endpoint

        self.kb_path = Path(kb_path)
        self.index_path = Path(index_path)
        self.stock_cache_path = Path(stock_cache_path)

    def sync_products_to_rag(self) -> EntegraSyncResult:
        if not self.enabled:
            raise RuntimeError("Entegra sync is disabled")

        products = self.fetch_products()
        normalized = [self._normalize_product(item) for item in products]
        normalized = [item for item in normalized if item is not None]

        existing = self._read_json_list(self.kb_path)
        merged = self._upsert_products(existing, normalized)
        self._write_json(self.kb_path, merged)

        index_docs = build_index(merged, chunk_size=500, overlap=100)
        self._write_json(self.index_path, index_docs)

        stock_map = self._build_stock_cache(normalized)
        self._write_json(self.stock_cache_path, stock_map)

        return EntegraSyncResult(
            products_fetched=len(products),
            products_upserted=len(normalized),
            index_chunks_written=len(index_docs),
            synced_at=datetime.now(timezone.utc).isoformat(),
        )

    def fetch_products(self) -> list[dict[str, Any]]:
        if not self.enabled:
            return []

        products: list[dict[str, Any]] = []
        for page in range(1, self.max_pages + 1):
            payload = self._request_json("GET", self._resolve_products_endpoint(page))
            page_items = self._extract_product_list(payload)
            if not page_items:
                break
            products.extend(page_items)
        return products

    def fetch_product_by_code(self, product_code: str) -> dict[str, Any] | None:
        for item in self.fetch_products():
            candidate = self._pick(item, ["productCode", "productcode", "barcode", "productId", "id"])
            if str(candidate) == str(product_code):
                return item
        return None

    def fetch_live_stock(self, product_id: str) -> int | None:
        if not self.enabled or not product_id:
            return None

        if self.stock_endpoint:
            endpoint = self.stock_endpoint
            if "{product_id}" in endpoint:
                endpoint = endpoint.replace("{product_id}", str(product_id))
                payload = self._request_json("GET", endpoint)
            else:
                payload = self._request_json("GET", endpoint, params={"product_id": product_id})

            stock_value = self._extract_stock(payload)
            if stock_value is not None:
                self._update_stock_cache_item(product_id, stock_value)
                return stock_value

        product = self.fetch_product_by_code(product_id)
        stock_value = self._extract_stock(product)
        if stock_value is not None:
            self._update_stock_cache_item(product_id, stock_value)
            return stock_value

        cached = self._read_stock_cache()
        return cached.get(str(product_id))

    def _resolve_products_endpoint(self, page: int) -> str:
        if "{page}" in self.products_endpoint:
            return self.products_endpoint.replace("{page}", str(page))
        if "page=" in self.products_endpoint:
            return self.products_endpoint.replace("page=1", f"page={page}")
        return f"{self.products_endpoint.rstrip('/')}/page={page}/"

    def _request_json(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._auth_headers()

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_payload,
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        return response.json()

    def _auth_headers(self) -> dict[str, str]:
        if self.auth_type in {"jwt", "bearer", "token"}:
            token = self.token or self._obtain_token()
            if token:
                return {"Authorization": f"JWT {token}"}

        headers: dict[str, str] = {}
        if self.api_key:
            headers[self.api_key_header] = self.api_key
        if self.api_secret:
            headers[self.api_secret_header] = self.api_secret
        return headers

    def _obtain_token(self) -> str:
        if self.token:
            return self.token
        if not self.username or not self.password:
            return ""

        payload = {
            "username": self.username,
            "password": self.password,
        }
        response = requests.post(
            f"{self.base_url}/{self.auth_endpoint.lstrip('/')}",
            json=payload,
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        data = response.json()
        self.token = str(data.get("access") or data.get("token") or "")
        return self.token

    @staticmethod
    def _normalize_product(raw: dict[str, Any]) -> dict[str, Any] | None:
        product_id = EntegraSyncService._pick(raw, ["productCode", "productcode", "barcode", "productId", "id"])
        if product_id is None:
            return None

        title = EntegraSyncService._pick(raw, ["productName", "name", "title"]) or f"Urun {product_id}"
        description = EntegraSyncService._pick(raw, ["description", "detail", "productDescription"]) or ""
        brand = EntegraSyncService._pick(raw, ["brand", "brandName"]) or ""
        category = EntegraSyncService._pick(raw, ["group", "category", "categoryName"]) or ""
        stock = EntegraSyncService._pick(raw, ["quantity", "stock", "qty", "availableStock"])
        price = EntegraSyncService._pick(raw, ["price1", "price", "salePrice", "listPrice"])
        barcode = EntegraSyncService._pick(raw, ["barcode"])
        variations = raw.get("variations") if isinstance(raw.get("variations"), list) else []

        details = [
            f"Urun adi: {title}",
            f"Aciklama: {description}" if description else "",
            f"Marka: {brand}" if brand else "",
            f"Kategori: {category}" if category else "",
            f"Barkod: {barcode}" if barcode else "",
            f"Fiyat: {price}" if price is not None else "",
        ]

        if variations:
            details.append(f"Varyant sayisi: {len(variations)}")

        return {
            "doc_id": f"entegra-{product_id}-product",
            "source_type": "product_spec",
            "channel": "site",
            "marketplace": "",
            "product_id": str(product_id),
            "title": str(title),
            "content": "\n".join([line for line in details if line]),
            "price": EntegraSyncService._parse_float(price),
            "stock": EntegraSyncService._parse_int(stock),
            "brand": brand or None,
            "category": str(category) if category else None,
            "barcode": str(barcode) if barcode else None,
            "updated_at": datetime.now(timezone.utc).date().isoformat(),
        }

    @staticmethod
    def _extract_product_list(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("items", "data", "products", "result", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    @staticmethod
    def _pick(item: dict[str, Any], keys: list[str]) -> Any:
        for key in keys:
            if key in item and item[key] is not None:
                return item[key]
        return None

    @staticmethod
    def _upsert_products(existing: list[dict[str, Any]], products: list[dict[str, Any]]) -> list[dict[str, Any]]:
        product_ids = {item.get("product_id") for item in products}
        kept = [
            doc for doc in existing
            if not (
                doc.get("source_type") == "product_spec"
                and str(doc.get("product_id")) in product_ids
                and str(doc.get("doc_id", "")).startswith("entegra-")
            )
        ]

        for product in products:
            kept.append(dict(product))

        return kept

    def _build_stock_cache(self, products: list[dict[str, Any]]) -> dict[str, int]:
        current = self._read_stock_cache()
        for product in products:
            product_id = product.get("product_id")
            stock = product.get("stock")
            if product_id is None or stock is None:
                continue
            parsed = self._parse_int(stock)
            if parsed is not None:
                current[str(product_id)] = parsed
        return current

    def _update_stock_cache_item(self, product_id: str, stock_value: int) -> None:
        current = self._read_stock_cache()
        current[str(product_id)] = stock_value
        self._write_json(self.stock_cache_path, current)

    def _read_stock_cache(self) -> dict[str, int]:
        if not self.stock_cache_path.exists():
            return {}
        with self.stock_cache_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            out: dict[str, int] = {}
            for key, value in data.items():
                parsed = self._parse_int(value)
                if parsed is not None:
                    out[str(key)] = parsed
            return out
        return {}

    @staticmethod
    def _extract_stock(payload: Any) -> int | None:
        if isinstance(payload, dict):
            for key in ("quantity", "stock", "qty", "availableStock"):
                if key in payload:
                    return EntegraSyncService._parse_int(payload.get(key))
            variations = payload.get("variations")
            if isinstance(variations, list) and variations:
                total = 0
                found = False
                for item in variations:
                    stock = EntegraSyncService._extract_stock(item)
                    if stock is not None:
                        total += stock
                        found = True
                if found:
                    return total
            for key in ("data", "result", "item"):
                nested = payload.get(key)
                if nested is not None:
                    stock = EntegraSyncService._extract_stock(nested)
                    if stock is not None:
                        return stock
        if isinstance(payload, list):
            for item in payload:
                stock = EntegraSyncService._extract_stock(item)
                if stock is not None:
                    return stock
        return None

    @staticmethod
    def _parse_int(value: Any) -> int | None:
        try:
            if value is None or value == "":
                return None
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_float(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _read_json_list(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
