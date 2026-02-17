# Settlements

Retrieve settlement results for resolved markets -- whether they settled "yes" or "no" and the final payout value.

## List Settlements

`list_settlements()` returns settlement results with optional filters:

```python
from kalshibook import KalshiBook

client = KalshiBook("kb-your-api-key")

settlements = client.list_settlements()

for s in settlements.data:
    print(
        f"{s.market_ticker}: result={s.result} "
        f"value={s.settlement_value} "
        f"settled_at={s.settled_at}"
    )
```

## Filter Settlements

Narrow results by event or outcome:

```python
# All settlements for a specific event
event_settlements = client.list_settlements(event_ticker="KXBTC-25FEB14")

for s in event_settlements.data:
    print(f"  {s.market_ticker}: {s.result}")

# Only "yes" settlements
yes_settlements = client.list_settlements(result="yes")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `event_ticker` | `str \| None` | Filter by parent event ticker |
| `result` | `str \| None` | Filter by settlement result (`"yes"`, `"no"`) |

## Get Single Settlement

`get_settlement()` returns the settlement for a specific market:

```python
settlement = client.get_settlement("KXBTC-25FEB14-T98250")

s = settlement.data
print(f"Market: {s.market_ticker}")
print(f"Event: {s.event_ticker}")
print(f"Result: {s.result}")
print(f"Settlement value: {s.settlement_value}")
print(f"Determined at: {s.determined_at}")
print(f"Settled at: {s.settled_at}")
```

## Convert to DataFrame

```python
settlements = client.list_settlements()
df = settlements.to_df()

print(df[["market_ticker", "result", "settlement_value", "settled_at"]])
```

!!! tip
    DataFrame conversion requires `pip install kalshibook[pandas]`.

## SettlementRecord Fields

| Field | Type | Description |
|-------|------|-------------|
| `market_ticker` | `str` | Market ticker |
| `event_ticker` | `str \| None` | Parent event ticker |
| `result` | `str \| None` | Settlement result (`"yes"` or `"no"`) |
| `settlement_value` | `int \| None` | Payout value in cents |
| `determined_at` | `datetime \| None` | When the result was determined |
| `settled_at` | `datetime \| None` | When settlement was processed |
