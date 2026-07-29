from __future__ import annotations

import heapq
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import replace as copy_dataclass

from .models import BookLevel, Order, OrderType, Side, Trade


class LimitOrderBook:
    """Single-symbol limit order book with price-time priority.

    Buy prices use a max heap represented by negative integer ticks. Sell
    prices use a normal min heap. Cancellations are lazy: canceled IDs are
    removed from the active-order map and stale heap entries are discarded
    when they reach the top.
    """

    def __init__(self, symbol: str, retain_trade_history: bool = True) -> None:
        if not symbol.strip():
            raise ValueError("symbol cannot be empty")
        self.symbol = symbol.upper()
        self._bids: list[tuple[int, int, str]] = []
        self._asks: list[tuple[int, int, str]] = []
        self._orders: dict[str, Order] = {}
        self._seen_order_ids: set[str] = set()
        self._trades: list[Trade] = []
        self._retain_trade_history = retain_trade_history
        self._max_total_quantity: dict[str, int] = {}
        self._order_sequence = 0
        self._trade_sequence = 0

    def submit_limit(
        self,
        order_id: str,
        side: Side,
        quantity: int,
        price_ticks: int,
    ) -> list[Trade]:
        """Submit a limit order and return trades produced immediately."""
        if price_ticks <= 0:
            raise ValueError("price_ticks must be positive")
        order = self._new_order(
            order_id=order_id,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price_ticks=price_ticks,
        )
        trades = self._match(order)
        if order.remaining:
            self._rest(order)
        return trades

    def submit_market(
        self,
        order_id: str,
        side: Side,
        quantity: int,
    ) -> list[Trade]:
        """Submit a market order; any quantity without liquidity is canceled."""
        order = self._new_order(
            order_id=order_id,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price_ticks=None,
        )
        return self._match(order)

    def cancel(self, order_id: str) -> Order:
        """Cancel a resting order and return its final state."""
        order = self._orders.pop(order_id, None)
        if order is None:
            raise KeyError(f"unknown active order: {order_id}")
        return copy_dataclass(order)

    def replace(
        self,
        order_id: str,
        new_quantity: int,
        new_price_ticks: int | None = None,
    ) -> list[Trade]:
        """Replace a resting order and return any immediately produced trades.

        ``new_quantity`` is the desired remaining quantity, not the original
        total quantity. Reducing quantity at the same price keeps time
        priority. Increasing quantity or changing price receives a new
        sequence number and therefore loses time priority.
        """
        if new_quantity <= 0:
            raise ValueError("new_quantity must be positive; use cancel instead")
        order = self._orders.get(order_id)
        if order is None:
            raise KeyError(f"unknown active order: {order_id}")

        price_ticks = order.price_ticks if new_price_ticks is None else new_price_ticks
        if price_ticks is None or price_ticks <= 0:
            raise ValueError("new_price_ticks must be positive")

        same_price = price_ticks == order.price_ticks
        if same_price and new_quantity <= order.remaining:
            filled = order.filled_quantity
            order.quantity = filled + new_quantity
            order.remaining = new_quantity
            return []

        self._orders.pop(order_id)
        filled = order.filled_quantity
        order.quantity = filled + new_quantity
        order.remaining = new_quantity
        order.price_ticks = price_ticks
        self._order_sequence += 1
        order.sequence = self._order_sequence
        self._max_total_quantity[order_id] = max(
            self._max_total_quantity[order_id],
            order.quantity,
        )

        trades = self._match(order)
        if order.remaining:
            self._rest(order)
        return trades

    def get_order(self, order_id: str) -> Order | None:
        """Return an active resting order, or None."""
        order = self._orders.get(order_id)
        return copy_dataclass(order) if order is not None else None

    def active_orders(self) -> tuple[Order, ...]:
        """Return immutable snapshots of active orders in arrival order."""
        return tuple(
            copy_dataclass(order)
            for order in sorted(self._orders.values(), key=lambda item: item.sequence)
        )

    def trade_history(self) -> tuple[Trade, ...]:
        """Return all trades in deterministic execution order."""
        return tuple(self._trades)

    def top_of_book(self) -> dict[str, BookLevel | None]:
        bids = self.depth(Side.BUY, levels=1)
        asks = self.depth(Side.SELL, levels=1)
        return {
            "bid": bids[0] if bids else None,
            "ask": asks[0] if asks else None,
        }

    def spread_ticks(self) -> int | None:
        top = self.top_of_book()
        if top["bid"] is None or top["ask"] is None:
            return None
        return top["ask"].price_ticks - top["bid"].price_ticks

    def midpoint_ticks(self) -> float | None:
        top = self.top_of_book()
        if top["bid"] is None or top["ask"] is None:
            return None
        return 0.5 * (top["ask"].price_ticks + top["bid"].price_ticks)

    def depth(self, side: Side, levels: int = 5) -> list[BookLevel]:
        """Aggregate active resting orders into sorted price levels."""
        if levels < 1:
            raise ValueError("levels must be positive")
        quantities: dict[int, int] = defaultdict(int)
        counts: dict[int, int] = defaultdict(int)
        for order in self._orders.values():
            if order.side is side and order.price_ticks is not None:
                quantities[order.price_ticks] += order.remaining
                counts[order.price_ticks] += 1
        prices: Iterable[int] = sorted(
            quantities,
            reverse=side is Side.BUY,
        )
        return [
            BookLevel(price, quantities[price], counts[price])
            for price in list(prices)[:levels]
        ]

    def active_order_count(self) -> int:
        return len(self._orders)

    def assert_invariants(self) -> None:
        """Raise ``AssertionError`` if internal book invariants are violated."""
        for order_id, order in self._orders.items():
            assert order_id == order.order_id
            assert order.order_type is OrderType.LIMIT
            assert order.price_ticks is not None and order.price_ticks > 0
            assert 0 < order.remaining <= order.quantity
            expected = self._heap_entry(order)
            heap = self._bids if order.side is Side.BUY else self._asks
            assert expected in heap, f"active order missing from heap: {order_id}"

        top = self.top_of_book()
        if top["bid"] is not None and top["ask"] is not None:
            assert top["bid"].price_ticks < top["ask"].price_ticks

        traded_by_order: dict[str, int] = defaultdict(int)
        last_sequence = 0
        for trade in self._trades:
            assert trade.sequence > last_sequence
            assert trade.quantity > 0
            assert trade.price_ticks > 0
            traded_by_order[trade.maker_order_id] += trade.quantity
            traded_by_order[trade.taker_order_id] += trade.quantity
            last_sequence = trade.sequence
        for order_id, quantity in traded_by_order.items():
            assert quantity <= self._max_total_quantity[order_id]

    def _new_order(
        self,
        order_id: str,
        side: Side,
        order_type: OrderType,
        quantity: int,
        price_ticks: int | None,
    ) -> Order:
        if not isinstance(side, Side):
            raise TypeError("side must be Side.BUY or Side.SELL")
        if not order_id.strip():
            raise ValueError("order_id cannot be empty")
        if order_id in self._orders:
            raise ValueError(f"duplicate active order_id: {order_id}")
        if order_id in self._seen_order_ids:
            raise ValueError(f"order_id has already been used: {order_id}")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self._order_sequence += 1
        order = Order(
            order_id=order_id,
            side=side,
            order_type=order_type,
            quantity=quantity,
            remaining=quantity,
            sequence=self._order_sequence,
            price_ticks=price_ticks,
        )
        self._seen_order_ids.add(order_id)
        self._max_total_quantity[order_id] = quantity
        return order

    def _match(self, incoming: Order) -> list[Trade]:
        trades: list[Trade] = []
        while incoming.remaining:
            resting = self._best_opposite(incoming.side)
            if resting is None or not self._crosses(incoming, resting):
                break

            quantity = min(incoming.remaining, resting.remaining)
            incoming.remaining -= quantity
            resting.remaining -= quantity
            self._trade_sequence += 1
            trade = Trade(
                sequence=self._trade_sequence,
                symbol=self.symbol,
                price_ticks=resting.price_ticks,  # type: ignore[arg-type]
                quantity=quantity,
                maker_order_id=resting.order_id,
                taker_order_id=incoming.order_id,
                taker_side=incoming.side,
            )
            trades.append(trade)
            if self._retain_trade_history:
                self._trades.append(trade)
            if resting.is_filled:
                self._orders.pop(resting.order_id, None)
                self._discard_stale_top(resting.side)
        return trades

    def _crosses(self, incoming: Order, resting: Order) -> bool:
        if incoming.order_type is OrderType.MARKET:
            return True
        if incoming.side is Side.BUY:
            return incoming.price_ticks >= resting.price_ticks  # type: ignore[operator]
        return incoming.price_ticks <= resting.price_ticks  # type: ignore[operator]

    def _rest(self, order: Order) -> None:
        if order.order_type is not OrderType.LIMIT or order.price_ticks is None:
            raise ValueError("only priced limit orders can rest")
        self._orders[order.order_id] = order
        entry = self._heap_entry(order)
        heapq.heappush(self._bids if order.side is Side.BUY else self._asks, entry)

    def _best_opposite(self, incoming_side: Side) -> Order | None:
        opposite = Side.SELL if incoming_side is Side.BUY else Side.BUY
        self._discard_stale_top(opposite)
        heap = self._asks if opposite is Side.SELL else self._bids
        return self._orders[heap[0][2]] if heap else None

    def _discard_stale_top(self, side: Side) -> None:
        heap = self._bids if side is Side.BUY else self._asks
        while heap:
            order = self._orders.get(heap[0][2])
            if (
                order is not None
                and order.remaining > 0
                and heap[0] == self._heap_entry(order)
            ):
                break
            heapq.heappop(heap)

    @staticmethod
    def _heap_entry(order: Order) -> tuple[int, int, str]:
        if order.price_ticks is None:
            raise ValueError("unpriced orders cannot be added to a price heap")
        return (
            -order.price_ticks if order.side is Side.BUY else order.price_ticks,
            order.sequence,
            order.order_id,
        )
