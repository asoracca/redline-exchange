"""Optional C++ core with the existing Python value objects at its boundary.

The reference engine remains the default for replay and market research.
"""

from .models import BookLevel, Order, OrderType, Side, Trade

MAX_VALUE = 2**53 - 1


def _integer(value, name):
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    if not 0 < value <= MAX_VALUE:
        raise ValueError(f"{name} must be in [1, {MAX_VALUE}]")
    return value


def _side(side):
    if not isinstance(side, Side):
        raise TypeError("side must be Side.BUY or Side.SELL")
    return side is Side.BUY


class NativeLimitOrderBook:
    def __init__(self, symbol: str, retain_trade_history: bool = True):
        from . import _native

        if not symbol.strip():
            raise ValueError("symbol cannot be empty")
        self.symbol = symbol.upper()
        self._core = _native.Book(retain_trade_history)

    def _trades(self, trades):
        return [
            Trade(
                t.sequence,
                self.symbol,
                t.price,
                t.quantity,
                t.maker,
                t.taker,
                Side.BUY if t.buy else Side.SELL,
            )
            for t in trades
        ]

    @staticmethod
    def _order(o):
        return Order(
            o.id,
            Side.BUY if o.buy else Side.SELL,
            OrderType.LIMIT,
            o.quantity,
            o.remaining,
            o.sequence,
            o.price,
        )

    def submit_limit(self, order_id, side, quantity, price_ticks):
        if not order_id.strip():
            raise ValueError("order_id cannot be empty")
        return self._trades(
            self._core.submit(
                order_id,
                _side(side),
                _integer(quantity, "quantity"),
                _integer(price_ticks, "price_ticks"),
                False,
            )
        )

    def submit_market(self, order_id, side, quantity):
        if not order_id.strip():
            raise ValueError("order_id cannot be empty")
        return self._trades(
            self._core.submit(
                order_id, _side(side), _integer(quantity, "quantity"), 0, True
            )
        )

    def cancel(self, order_id):
        try:
            return self._order(self._core.cancel(order_id))
        except IndexError as error:
            raise KeyError(order_id) from error

    def replace(self, order_id, new_quantity, new_price_ticks=None):
        quantity = _integer(new_quantity, "new_quantity")
        price = (
            0
            if new_price_ticks is None
            else _integer(new_price_ticks, "new_price_ticks")
        )
        try:
            return self._trades(self._core.replace(order_id, quantity, price))
        except IndexError as error:
            raise KeyError(order_id) from error

    def active_orders(self):
        return tuple(self._order(o) for o in self._core.active())

    def get_order(self, order_id):
        order = self._core.get(order_id)
        return None if order is None else self._order(order)

    def trade_history(self):
        return tuple(self._trades(self._core.history()))

    def active_order_count(self):
        return self._core.count()

    def depth(self, side, levels=5):
        return [
            BookLevel(level.price, level.quantity, level.count)
            for level in self._core.depth(_side(side), _integer(levels, "levels"))
        ]

    def top_of_book(self):
        bids, asks = self.depth(Side.BUY, 1), self.depth(Side.SELL, 1)
        return {"bid": bids[0] if bids else None, "ask": asks[0] if asks else None}

    def spread_ticks(self):
        top = self.top_of_book()
        return (
            None
            if None in top.values()
            else top["ask"].price_ticks - top["bid"].price_ticks
        )

    def midpoint_ticks(self):
        top = self.top_of_book()
        return (
            None
            if None in top.values()
            else (top["ask"].price_ticks + top["bid"].price_ticks) / 2
        )

    def assert_invariants(self):
        self._core.check()
