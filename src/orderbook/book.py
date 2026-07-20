from __future__ import annotations

import heapq
from collections import defaultdict
from collections.abc import Iterable

from .models import BookLevel, Order, OrderType, Side, Trade


class LimitOrderBook:
    """Single-symbol limit order book with price-time priority.

    Buy prices use a max heap represented by negative integer ticks. Sell
    prices use a normal min heap. Cancellations are lazy: canceled IDs are
    removed from the active-order map and stale heap entries are discarded
    when they reach the top.
    """

    def __init__(self, symbol: str) -> None:
        if not symbol.strip():
            raise ValueError("symbol cannot be empty")
        self.symbol = symbol.upper()
        self._bids: list[tuple[int, int, str]] = []
        self._asks: list[tuple[int, int, str]] = []
        self._orders: dict[str, Order] = {}
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
        return order

    def get_order(self, order_id: str) -> Order | None:
        """Return an active resting order, or None."""
        return self._orders.get(order_id)

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
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self._order_sequence += 1
        return Order(
            order_id=order_id,
            side=side,
            order_type=order_type,
            quantity=quantity,
            remaining=quantity,
            sequence=self._order_sequence,
            price_ticks=price_ticks,
        )

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
            trades.append(
                Trade(
                    sequence=self._trade_sequence,
                    symbol=self.symbol,
                    price_ticks=resting.price_ticks,  # type: ignore[arg-type]
                    quantity=quantity,
                    maker_order_id=resting.order_id,
                    taker_order_id=incoming.order_id,
                    taker_side=incoming.side,
                )
            )
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
        entry = (
            -order.price_ticks if order.side is Side.BUY else order.price_ticks,
            order.sequence,
            order.order_id,
        )
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
            if order is not None and order.remaining > 0:
                break
            heapq.heappop(heap)
