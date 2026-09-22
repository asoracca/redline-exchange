from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

Symbol = Literal["AAPL", "MSFT", "NVDA", "DEMO"]
Number = Annotated[int, Field(strict=True, ge=1, le=1_000_000)]
ID = Annotated[str, Field(strict=True, pattern=r"^[A-Za-z0-9_-]{1,64}$")]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BaseCommand(Model):
    request_id: ID
    symbol: Symbol


class Limit(BaseCommand):
    kind: Literal["LIMIT"]
    order_id: ID
    side: Literal["BUY", "SELL"]
    quantity: Number
    price_ticks: Number


class Market(BaseCommand):
    kind: Literal["MARKET"]
    order_id: ID
    side: Literal["BUY", "SELL"]
    quantity: Number


class Cancel(BaseCommand):
    kind: Literal["CANCEL"]
    order_id: ID


class Replace(BaseCommand):
    kind: Literal["REPLACE"]
    order_id: ID
    quantity: Number
    price_ticks: Number | None = None


class Reset(BaseCommand):
    kind: Literal["RESET"]


Command = Annotated[
    Limit | Market | Cancel | Replace | Reset, Field(discriminator="kind")
]


class Trade(Model):
    sequence: int
    symbol: Symbol
    price_ticks: int
    quantity: int
    maker_order_id: str
    taker_order_id: str
    taker_side: Literal["BUY", "SELL"]


class Level(Model):
    price_ticks: int
    quantity: int
    order_count: int


class Order(Model):
    order_id: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["LIMIT", "MARKET"]
    quantity: int
    remaining: int
    sequence: int
    price_ticks: int | None


class Book(Model):
    bids: list[Level]
    asks: list[Level]
    orders: list[Order]
    trades: list[Trade]
    epoch: int


class Snapshot(Model):
    session_id: str
    seq: int
    mode: Literal["synthetic simulation"] = "synthetic simulation"
    backend: Literal["python", "cpp"]
    books: dict[str, Book]


class Event(Model):
    seq: int
    command: Command
    accepted: bool
    error: str | None
    trades: list[Trade]


class ReplayResult(Model):
    verified: bool
    snapshot: Snapshot
