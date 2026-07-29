# Deterministic event replay

Redline can rebuild a book from an ordered CSV stream. Rows are applied from
top to bottom, and the book checks its invariants after every event.

## Schema

The header must be exactly:

```text
event_type,order_id,side,quantity,price_ticks
```

| Event | Required fields | Meaning |
|---|---|---|
| `LIMIT` | ID, side, quantity, price | Submit a priced order. |
| `MARKET` | ID, side, quantity | Trade against available opposite liquidity. |
| `CANCEL` | ID | Remove an active resting order. |
| `REPLACE` | ID, quantity; price optional | Change remaining quantity and optionally price. |

Blank fields are intentional. For `REPLACE`, a blank price keeps the current
price. Quantity is always the desired **remaining** quantity.

## Run

```bash
redline-replay examples/events.csv --symbol DEMO
```

Malformed rows identify their CSV line. Valid rows that cannot be applied,
such as cancelling an unknown order, identify their event number. Replay is
strict: it stops at the first invalid event rather than silently changing the
event stream.
