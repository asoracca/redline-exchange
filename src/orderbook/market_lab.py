from __future__ import annotations

import csv
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from .book import LimitOrderBook
from .models import Side, Trade


@dataclass(frozen=True)
class SimulationConfig:
    steps: int = 1_000
    seed: int = 7
    initial_fair_value_ticks: int = 10_000
    volatility_ticks: int = 4
    half_spread_ticks: int = 3
    order_quantity: int = 10
    informed_share: float = 0.25
    inventory_skew: float = 0.05
    max_inventory: int = 100
    quote_refresh_interval: int = 1

    def __post_init__(self) -> None:
        if self.steps < 1:
            raise ValueError("steps must be positive")
        if self.initial_fair_value_ticks < 1:
            raise ValueError("initial fair value must be positive")
        if self.volatility_ticks < 0 or self.half_spread_ticks < 1:
            raise ValueError("volatility must be nonnegative and spread positive")
        if self.order_quantity < 1 or self.max_inventory < self.order_quantity:
            raise ValueError("invalid order quantity or inventory limit")
        if not 0 <= self.informed_share <= 1:
            raise ValueError("informed_share must be between zero and one")
        if self.quote_refresh_interval < 1:
            raise ValueError("quote_refresh_interval must be positive")


@dataclass(frozen=True)
class StepRecord:
    step: int
    fair_value_ticks: int
    spread_ticks: int | None
    inventory: int
    cash_ticks: int
    marked_pnl_ticks: int
    trader_type: str
    trade_count: int
    traded_quantity: int


@dataclass
class SimulationResult:
    config: SimulationConfig
    records: list[StepRecord]
    trades: list[Trade]
    informed_trade_quantity: int
    maker_edge_tick_quantity: int

    def summary(self) -> dict[str, float | int]:
        final = self.records[-1]
        total_quantity = sum(record.traded_quantity for record in self.records)
        spreads = [
            record.spread_ticks
            for record in self.records
            if record.spread_ticks is not None
        ]
        return {
            "ending_pnl_ticks": final.marked_pnl_ticks,
            "max_abs_inventory": max(abs(record.inventory) for record in self.records),
            "mean_spread_ticks": sum(spreads) / len(spreads) if spreads else 0.0,
            "fills": len(self.trades),
            "volume": total_quantity,
            "informed_volume_share": (
                self.informed_trade_quantity / total_quantity if total_quantity else 0.0
            ),
            "maker_edge_ticks_per_unit": (
                self.maker_edge_tick_quantity / total_quantity
                if total_quantity
                else 0.0
            ),
        }

    def write_records_csv(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(asdict(self.records[0])))
            writer.writeheader()
            writer.writerows(asdict(record) for record in self.records)


class NoiseTrader:
    name = "noise"

    @staticmethod
    def choose_side(rng: random.Random, *_: object) -> Side:
        return rng.choice((Side.BUY, Side.SELL))


class InformedTrader:
    name = "informed"

    @staticmethod
    def choose_side(
        _rng: random.Random,
        fair_value_ticks: int,
        book: LimitOrderBook,
    ) -> Side | None:
        top = book.top_of_book()
        ask = top["ask"]
        bid = top["bid"]
        if ask is not None and fair_value_ticks > ask.price_ticks:
            return Side.BUY
        if bid is not None and fair_value_ticks < bid.price_ticks:
            return Side.SELL
        return None


class InventoryAwareMarketMaker:
    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.inventory = 0
        self.cash_ticks = 0
        self._active_ids: set[str] = set()

    def refresh_quotes(
        self,
        book: LimitOrderBook,
        fair_value_ticks: int,
        step: int,
    ) -> None:
        for order_id in tuple(self._active_ids):
            if book.get_order(order_id) is not None:
                book.cancel(order_id)
        self._active_ids.clear()

        reservation = round(
            fair_value_ticks - self.config.inventory_skew * self.inventory
        )
        bid = max(1, reservation - self.config.half_spread_ticks)
        ask = max(bid + 1, reservation + self.config.half_spread_ticks)

        if self.inventory + self.config.order_quantity <= self.config.max_inventory:
            bid_id = f"mm-bid-{step}"
            book.submit_limit(bid_id, Side.BUY, self.config.order_quantity, bid)
            self._active_ids.add(bid_id)
        if self.inventory - self.config.order_quantity >= -self.config.max_inventory:
            ask_id = f"mm-ask-{step}"
            book.submit_limit(ask_id, Side.SELL, self.config.order_quantity, ask)
            self._active_ids.add(ask_id)

    def process_trades(self, trades: list[Trade], fair_value_ticks: int) -> int:
        edge = 0
        for trade in trades:
            if not trade.maker_order_id.startswith("mm-"):
                continue
            if trade.taker_side is Side.BUY:
                self.inventory -= trade.quantity
                self.cash_ticks += trade.price_ticks * trade.quantity
                edge += (trade.price_ticks - fair_value_ticks) * trade.quantity
            else:
                self.inventory += trade.quantity
                self.cash_ticks -= trade.price_ticks * trade.quantity
                edge += (fair_value_ticks - trade.price_ticks) * trade.quantity
        return edge

    def marked_pnl(self, fair_value_ticks: int) -> int:
        return self.cash_ticks + self.inventory * fair_value_ticks


def run_market_simulation(config: SimulationConfig) -> SimulationResult:
    """Run a deterministic artificial market around the matching engine.

    The fundamental value moves before traders act. Traders therefore interact
    with the market maker's previous quote, making quote-refresh latency and
    adverse selection visible without changing the matching engine itself.
    """
    rng = random.Random(config.seed)
    book = LimitOrderBook("RDLN")
    maker = InventoryAwareMarketMaker(config)
    noise = NoiseTrader()
    informed = InformedTrader()
    fair_value = config.initial_fair_value_ticks
    maker.refresh_quotes(book, fair_value, step=0)

    records: list[StepRecord] = []
    all_trades: list[Trade] = []
    informed_quantity = 0
    maker_edge = 0

    for step in range(1, config.steps + 1):
        fair_value = max(
            1,
            fair_value + rng.randint(-config.volatility_ticks, config.volatility_ticks),
        )
        trader = informed if rng.random() < config.informed_share else noise
        side = trader.choose_side(rng, fair_value, book)
        trades: list[Trade] = []
        if side is not None:
            trades = book.submit_market(
                f"{trader.name}-{step}", side, config.order_quantity
            )
            maker_edge += maker.process_trades(trades, fair_value)
            if trader is informed:
                informed_quantity += sum(trade.quantity for trade in trades)
            all_trades.extend(trades)

        if step % config.quote_refresh_interval == 0:
            maker.refresh_quotes(book, fair_value, step)

        quantity = sum(trade.quantity for trade in trades)
        records.append(
            StepRecord(
                step=step,
                fair_value_ticks=fair_value,
                spread_ticks=book.spread_ticks(),
                inventory=maker.inventory,
                cash_ticks=maker.cash_ticks,
                marked_pnl_ticks=maker.marked_pnl(fair_value),
                trader_type=trader.name,
                trade_count=len(trades),
                traded_quantity=quantity,
            )
        )

    return SimulationResult(
        config=config,
        records=records,
        trades=all_trades,
        informed_trade_quantity=informed_quantity,
        maker_edge_tick_quantity=maker_edge,
    )
