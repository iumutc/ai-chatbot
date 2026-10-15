from app.integrations.entegra import EntegraSyncService
from app.providers.base import ProductSnapshot


class EntegraChannelProvider:
    def __init__(self, service: EntegraSyncService):
        self.service = service

    def get_product_snapshot(self, product_id: str, channel: str | None = None) -> ProductSnapshot | None:
        if not self.service.enabled:
            return None

        try:
            item = self.service.fetch_product_by_code(product_id)
        except Exception:
            return None

        if not item:
            return None

        name = item.get("productName") or item.get("name") or item.get("title")
        description = item.get("description") or item.get("detail") or item.get("productDescription")
        price = _to_float(item.get("price1") or item.get("price") or item.get("salePrice") or item.get("listPrice"))
        stock = _to_int(item.get("quantity") or item.get("stock") or item.get("qty") or item.get("availableStock"))

        return ProductSnapshot(
            product_id=str(product_id),
            name=name,
            description=description,
            price=price,
            stock=stock,
            channel=channel,
            source="entegra",
        )

    def get_stock(self, product_id: str, channel: str | None = None) -> int | None:
        return self.service.fetch_live_stock(product_id)


def _to_int(value) -> int | None:
    try:
        if value is None:
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
