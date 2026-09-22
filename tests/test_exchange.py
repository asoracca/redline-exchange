import importlib.util
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from exchange.api import create_app
from exchange.schemas import Command
from exchange.service import Exchange, Conflict


def command(i, symbol="DEMO", **kwargs):
    return TypeAdapter(Command).validate_python(
        dict(request_id=str(i), symbol=symbol, **kwargs)
    )


BACKENDS = ["python"] + (
    ["cpp"] if importlib.util.find_spec("orderbook._native") else []
)


@pytest.mark.parametrize("backend", BACKENDS)
def test_isolation_priority_recovery_and_replay(tmp_path, backend):
    path = str(tmp_path / "events.db")
    e = Exchange(path, backend)
    for c in [
        command(
            1,
            kind="LIMIT",
            order_id="high",
            side="SELL",
            quantity=100,
            price_ticks=10105,
        ),
        command(
            2,
            kind="LIMIT",
            order_id="low",
            side="SELL",
            quantity=100,
            price_ticks=10100,
        ),
        command(
            3,
            "MSFT",
            kind="LIMIT",
            order_id="low",
            side="BUY",
            quantity=100,
            price_ticks=20000,
        ),
        command(4, kind="MARKET", order_id="buyer", side="BUY", quantity=130),
    ]:
        result = e.submit(c)
    assert [(t.quantity, t.price_ticks) for t in result.trades] == [
        (100, 10100),
        (30, 10105),
    ]
    assert len(e.snapshot().books["MSFT"].orders) == 1
    assert e.submit(c) == result
    with pytest.raises(Conflict):
        e.submit(command(4, kind="RESET"))
    rejected = e.submit(command(5, kind="CANCEL", order_id="missing"))
    assert not rejected.accepted
    assert e.submit(command(5, kind="CANCEL", order_id="missing")) == rejected
    expected = e.snapshot()
    assert e.replay() == expected
    e.close()
    e = Exchange(path, backend)
    assert e.snapshot() == expected
    events, snap = e.catchup(2)
    assert [x.seq for x in events] == [3, 4, 5]
    assert snap == expected
    e.submit(command(6, kind="RESET"))
    assert not e.snapshot().books["DEMO"].trades
    assert e.replay(5) == expected
    with pytest.raises(sqlite3.IntegrityError):
        e.db.execute("DELETE FROM events")
    e.close()


@pytest.mark.parametrize("backend", BACKENDS)
def test_fifo_replace_and_concurrent_serialization(backend):
    e = Exchange(":memory:", backend)
    with ThreadPoolExecutor(8) as pool:
        events = list(
            pool.map(
                lambda i: e.submit(
                    command(
                        i,
                        kind="LIMIT",
                        order_id=str(i),
                        side="SELL",
                        quantity=10,
                        price_ticks=10100,
                    )
                ),
                range(40),
            )
        )
    ordered = sorted(events, key=lambda x: x.seq)
    result = e.submit(
        command("buy", kind="MARKET", order_id="buy", side="BUY", quantity=400)
    )
    assert [t.maker_order_id for t in result.trades] == [
        x.command.order_id for x in ordered
    ]
    assert e.replay() == e.snapshot()
    e.close()


def test_api_validation_idempotency_reset_and_replay():
    with TestClient(create_app(":memory:")) as client:
        valid = dict(
            request_id="one",
            symbol="AAPL",
            kind="LIMIT",
            order_id="a",
            side="BUY",
            quantity=10,
            price_ticks=10000,
        )
        for bad in [True, 1.2, "10", 0, 1000001]:
            assert (
                client.post(
                    "/api/commands", json={**valid, "quantity": bad}
                ).status_code
                == 422
            )
        assert client.get("/api/snapshot").json()["seq"] == 0
        first = client.post("/api/commands", json=valid)
        assert first.status_code == 200
        assert client.post("/api/commands", json=valid).json() == first.json()
        assert (
            client.post("/api/commands", json={**valid, "quantity": 2}).status_code
            == 409
        )
        assert (
            client.post(
                "/api/commands", json=valid, headers={"origin": "http://evil.example"}
            ).status_code
            == 403
        )
        assert (
            client.get("/api/replay").json()["snapshot"]
            == client.get("/api/snapshot").json()
        )
        assert client.get("/api/events?cursor=999").status_code == 409
        assert client.get("/api/replay?through=999").status_code == 409
        assert client.post(
            "/api/commands", json=dict(request_id="reset", symbol="AAPL", kind="RESET")
        ).json()["accepted"]
        assert not client.get("/api/snapshot").json()["books"]["AAPL"]["orders"]


def test_transaction_failure_restores_book():
    e = Exchange(":memory:")
    e.db.execute(
        "CREATE TRIGGER fail BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'disk failure'); END"
    )
    with pytest.raises(sqlite3.IntegrityError):
        e.submit(
            command(
                1, kind="LIMIT", order_id="a", side="BUY", quantity=10, price_ticks=1
            )
        )
    assert e.snapshot().seq == 0
    assert not e.snapshot().books["DEMO"].orders
    e.db.execute("DROP TRIGGER fail")
    assert e.submit(
        command(1, kind="LIMIT", order_id="a", side="BUY", quantity=10, price_ticks=1)
    ).accepted
    e.close()


def test_single_process_lease(tmp_path):
    path = str(tmp_path / "one.db")
    e = Exchange(path)
    with pytest.raises(RuntimeError, match="already open"):
        Exchange(path)
    e.close()


def test_limits_validation_and_reset_scope(monkeypatch):
    import exchange.service

    monkeypatch.setattr(exchange.service, "MAX_EVENTS", 2)
    with TestClient(create_app(":memory:")) as client:
        assert (
            client.post(
                "/api/commands",
                content=b"x" * 4097,
                headers={"content-type": "application/json"},
            ).status_code
            == 413
        )
        base = dict(request_id="same", symbol="DEMO", kind="RESET")
        for bad in [
            dict(base, symbol="BAD"),
            dict(base, extra=1),
            dict(base, request_id="bad id"),
        ]:
            assert client.post("/api/commands", json=bad).status_code == 422
        first = client.post("/api/commands", json=base).json()
        assert (
            client.post("/api/commands", json=dict(base, request_id="second")).json()[
                "seq"
            ]
            == 2
        )
        assert client.post("/api/commands", json=base).json() == first
        assert (
            client.post(
                "/api/commands", json=dict(base, request_id="third")
            ).status_code
            == 429
        )
        assert client.get("/api/replay").json()["verified"]
