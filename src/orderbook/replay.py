from __future__ import annotations

import csv
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO, cast

from .book import LimitOrderBook
from .models import EventType, OrderEvent, Side, Trade


@dataclass(frozen=True)
class ReplayResult:
    book: LimitOrderBook
    events_processed: int
    trades: tuple[Trade, ...]


def read_events(source: str | Path | TextIO) -> tuple[OrderEvent, ...]:
    """Parse order events from CSV and report malformed rows precisely."""
    with ExitStack() as stack:
        if hasattr(source, "read"):
            handle = cast(TextIO, source)
        else:
            handle = stack.enter_context(
                Path(source).open("r", newline="", encoding="utf-8")
            )
        reader = csv.DictReader(handle)
        required = ["event_type", "order_id", "side", "quantity", "price_ticks"]
        if reader.fieldnames != required:
            raise ValueError(
                "CSV header must be: event_type,order_id,side,quantity,price_ticks"
            )
        events: list[OrderEvent] = []
        for line_number, row in enumerate(reader, start=2):
            try:
                event_type = EventType(row["event_type"].strip().upper())
                order_id = row["order_id"].strip()
                if not order_id:
                    raise ValueError("order_id cannot be empty")
                side_text = row["side"].strip().upper()
                quantity_text = row["quantity"].strip()
                price_text = row["price_ticks"].strip()
                side = Side(side_text) if side_text else None
                quantity = int(quantity_text) if quantity_text else None
                price_ticks = int(price_text) if price_text else None
                events.append(
                    OrderEvent(
                        event_type=event_type,
                        order_id=order_id,
                        side=side,
                        quantity=quantity,
                        price_ticks=price_ticks,
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"invalid event on CSV line {line_number}: {exc}"
                ) from exc
        return tuple(events)


def replay_events(
    events: tuple[OrderEvent, ...] | list[OrderEvent],
    symbol: str = "REPLAY",
    book: LimitOrderBook | None = None,
) -> ReplayResult:
    """Apply events in input order and return the reconstructed book."""
    target = book if book is not None else LimitOrderBook(symbol)
    trades: list[Trade] = []
    for event_number, event in enumerate(events, start=1):
        try:
            if event.event_type is EventType.LIMIT:
                _require(event, "side", "quantity", "price_ticks")
                trades.extend(
                    target.submit_limit(
                        event.order_id,
                        event.side,  # type: ignore[arg-type]
                        event.quantity,  # type: ignore[arg-type]
                        event.price_ticks,  # type: ignore[arg-type]
                    )
                )
            elif event.event_type is EventType.MARKET:
                _require(event, "side", "quantity")
                trades.extend(
                    target.submit_market(
                        event.order_id,
                        event.side,  # type: ignore[arg-type]
                        event.quantity,  # type: ignore[arg-type]
                    )
                )
            elif event.event_type is EventType.CANCEL:
                target.cancel(event.order_id)
            elif event.event_type is EventType.REPLACE:
                _require(event, "quantity")
                trades.extend(
                    target.replace(
                        event.order_id,
                        event.quantity,  # type: ignore[arg-type]
                        event.price_ticks,
                    )
                )
            target.assert_invariants()
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"failed to apply event {event_number} ({event.event_type.value} "
                f"{event.order_id}): {exc}"
            ) from exc
    return ReplayResult(target, len(events), tuple(trades))


def replay_csv(
    source: str | Path | TextIO,
    symbol: str = "REPLAY",
    book: LimitOrderBook | None = None,
) -> ReplayResult:
    return replay_events(read_events(source), symbol=symbol, book=book)


def _require(event: OrderEvent, *fields: str) -> None:
    missing = [field for field in fields if getattr(event, field) is None]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
