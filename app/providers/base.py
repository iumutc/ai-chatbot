from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProductSnapshot:
    product_id: str
    name: str | None
    description: str | None
    price: float | None
    stock: int | None
    channel: str | None
    source: str


class ChannelDataProvider(Protocol):
    def get_product_snapshot(self, product_id: str, channel: str | None = None) -> ProductSnapshot | None:
        ...

    def get_stock(self, product_id: str, channel: str | None = None) -> int | None:
        ...
