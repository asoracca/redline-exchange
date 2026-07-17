from __future__ import annotations

from .book import LimitOrderBook
from .models import Side


def money(ticks: int | float | None) -> str:
    return "-" if ticks is None else f"${ticks / 100:,.2f}"


def main() -> None:
    book = LimitOrderBook("DEMO")
    book.submit_limit("ask-1", Side.SELL, 100, 10_100)
    book.submit_limit("ask-2", Side.SELL, 75, 10_105)
    book.submit_limit("bid-1", Side.BUY, 90, 10_090)
    book.submit_limit("bid-2", Side.BUY, 50, 10_085)

    print("Initial top of book")
    print(book.top_of_book())
    print(f"Spread: {book.spread_ticks()} ticks")

    print("\nIncoming market buy for 130 shares")
    trades = book.submit_market("market-buy-1", Side.BUY, 130)
    for trade in trades:
        print(
            f"trade={trade.sequence} qty={trade.quantity} "
            f"price={money(trade.price_ticks)} maker={trade.maker_order_id}"
        )

    print("\nFinal depth")
    print("Bids:", book.depth(Side.BUY))
    print("Asks:", book.depth(Side.SELL))


if __name__ == "__main__":
    main()

