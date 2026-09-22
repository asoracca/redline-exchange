import importlib.util
import pytest
from orderbook import LimitOrderBook, Side

BACKENDS = [LimitOrderBook]
if importlib.util.find_spec("orderbook._native"):
    from orderbook.native import NativeLimitOrderBook

    BACKENDS.append(NativeLimitOrderBook)


@pytest.mark.parametrize("factory", BACKENDS)
@pytest.mark.parametrize("bad", [True, 1.5, float("nan"), float("inf"), "10"])
def test_integer_contract_and_atomicity(factory, bad):
    book = factory("TEST")
    for args in [(bad, 10), (10, bad)]:
        with pytest.raises(TypeError):
            book.submit_limit("new", Side.BUY, *args)
        assert book.active_order_count() == 0
    book.submit_limit("new", Side.BUY, 10, 10)
    before = book.active_orders()
    for args in [(bad, None), (10, bad)]:
        with pytest.raises(TypeError):
            book.replace("new", *args)
        assert book.active_orders() == before


@pytest.mark.parametrize("factory", BACKENDS)
def test_market_empty_invalid_side_and_duplicate_filled(factory):
    book = factory("TEST")
    assert book.submit_market("empty", Side.BUY, 1) == []
    with pytest.raises(ValueError):
        book.submit_market("empty", Side.BUY, 1)
    with pytest.raises(TypeError):
        book.submit_limit("a", "BUY", 1, 10)
    book.submit_limit("a", Side.BUY, 1, 10)
