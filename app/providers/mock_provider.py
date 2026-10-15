import json
from pathlib import Path
from typing import Any

from app.providers.base import ProductSnapshot


class MockChannelProvider:
    def __init__(self, kb_path: str):
        self.kb_path = Path(kb_path)
        self._docs = self._load_docs()

    def get_product_snapshot(self, product_id: str, channel: str | None = None) -> ProductSnapshot | None:
        docs = [doc for doc in self._docs if str(doc.get("product_id")) == str(product_id)]
        if not docs:
            return None

        product_doc = self._select_doc(docs, "product_spec", channel)
        if product_doc is None:
            product_doc = docs[0]

        name = product_doc.get("title")
        description = product_doc.get("content")
        stock = self._extract_number(product_doc, ["stock", "quantity", "qty", "availableStock"])
        price = self._extract_float(product_doc, ["price", "salePrice", "listPrice"])

        return ProductSnapshot(
            product_id=str(product_id),
            name=name,
            description=description,
            price=price,
            stock=stock,
            channel=channel,
            source="mock",
        )

    def get_stock(self, product_id: str, channel: str | None = None) -> int | None:
        snapshot = self.get_product_snapshot(product_id, channel)
        return snapshot.stock if snapshot else None

    def _select_doc(self, docs: list[dict[str, Any]], source_type: str, channel: str | None) -> dict[str, Any] | None:
        by_type = [doc for doc in docs if doc.get("source_type") == source_type]
        if not by_type:
            return None
        if not channel:
            return by_type[0]

        lowered = channel.lower()
        for doc in by_type:
            doc_channel = str(doc.get("channel", "")).lower()
            marketplace = str(doc.get("marketplace", "")).lower()
            if doc_channel == lowered or marketplace == lowered:
                return doc
        return by_type[0]

    def _load_docs(self) -> list[dict[str, Any]]:
        if not self.kb_path.exists():
            return []
        with self.kb_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []

    @staticmethod
    def _extract_number(doc: dict[str, Any], keys: list[str]) -> int | None:
        for key in keys:
            if key in doc and doc[key] is not None:
                try:
                    return int(float(doc[key]))
                except (TypeError, ValueError):
                    continue
        return None

    @staticmethod
    def _extract_float(doc: dict[str, Any], keys: list[str]) -> float | None:
        for key in keys:
            if key in doc and doc[key] is not None:
                try:
                    return float(doc[key])
                except (TypeError, ValueError):
                    continue
        return None
