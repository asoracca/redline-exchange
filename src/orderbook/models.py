from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class EventType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    CANCEL = "CANCEL"
    REPLACE = "REPLACE"


@dataclass
class Order:
    order_id: str
    side: Side
    order_type: OrderType
    quantity: int
    remaining: int
    sequence: int
    price_ticks: int | None = None

    @property
    def filled_quantity(self) -> int:
        return self.quantity - self.remaining

    @property
    def is_filled(self) -> bool:
        return self.remaining == 0


@dataclass(frozen=True)
class Trade:
    sequence: int
    symbol: str
    price_ticks: int
    quantity: int
    maker_order_id: str
    taker_order_id: str
    taker_side: Side


@dataclass(frozen=True)
class BookLevel:
    price_ticks: int
    quantity: int
    order_count: int


@dataclass(frozen=True)
class OrderEvent:
    event_type: EventType
    order_id: str
    side: Side | None = None
    quantity: int | None = None
    price_ticks: int | None = None
