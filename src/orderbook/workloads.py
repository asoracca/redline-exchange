"""Seeded, pre-generated API calls shared by both engines and the profiler."""

from dataclasses import asdict
import hashlib
import json
import random

from .book import LimitOrderBook
from .models import Side

WORKLOADS = ("crossing", "resting", "cancel_replace", "mixed")


def generate(count=10_000, seed=17, workload="crossing"):
    if count < 1 or workload not in WORKLOADS:
        raise ValueError("positive count and a known workload required")
    rng = random.Random(seed)
    events = []
    shadow = LimitOrderBook("BENCH", retain_trade_history=False)
    ids = []
    for i in range(count):
        side = Side.BUY if rng.random() < 0.5 else Side.SELL
        qty = rng.randint(1, 500)
        price = 10_000 + rng.randint(-20, 20)
        event = ("submit_limit", f"order-{i}", side, qty, price)
        if workload == "resting":
            event = (
                "submit_limit",
                f"order-{i}",
                side,
                qty,
                9900 - i % 100 if side is Side.BUY else 10100 + i % 100,
            )
        elif workload == "cancel_replace":
            group, phase = divmod(i, 4)
            oid = f"cycle-{group}"
            event = [
                ("submit_limit", oid, Side.BUY, 100, 9900),
                ("replace", oid, 50, None),
                ("replace", oid, 150, 9899),
                ("cancel", oid),
            ][phase]
        elif workload == "mixed":
            choice = rng.random()
            candidate = rng.choice(ids) if ids else None
            if choice < 0.15:
                event = ("submit_market", f"order-{i}", side, qty)
            elif choice < 0.45 and candidate and shadow.get_order(candidate):
                event = (
                    ("cancel", candidate)
                    if choice < 0.30
                    else ("replace", candidate, qty, price)
                )
        apply(shadow, event)
        if event[0].startswith("submit"):
            ids.append(event[1])
        events.append(event)
    return events


def apply(book, event):
    return getattr(book, event[0])(*event[1:])


def workload_hash(events):
    return hashlib.sha256(
        json.dumps(events, separators=(",", ":")).encode()
    ).hexdigest()


def replay(book, events):
    trade_count = 0
    for event in events:
        result = apply(book, event)
        if isinstance(result, list):
            trade_count += len(result)
    return trade_count


def verify(factory, events):
    """Compare every response and final full state, outside any timed region."""
    reference, candidate = LimitOrderBook("BENCH"), factory("BENCH")
    digest = hashlib.sha256()
    for index, event in enumerate(events):
        left, right = apply(reference, event), apply(candidate, event)
        if left != right:
            raise AssertionError(f"backend response mismatch at event {index}: {event}")
        values = [asdict(t) for t in left] if isinstance(left, list) else asdict(left)
        digest.update(json.dumps(values, sort_keys=True).encode())
    if reference.active_orders() != candidate.active_orders():
        raise AssertionError("final active state mismatch")
    if reference.trade_history() != candidate.trade_history():
        raise AssertionError("trade history mismatch")
    digest.update(
        json.dumps(
            [asdict(o) for o in reference.active_orders()], sort_keys=True
        ).encode()
    )
    return digest.hexdigest()
