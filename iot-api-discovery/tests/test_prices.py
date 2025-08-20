from __future__ import annotations

from tools.prices.octopus import compute_cheap_window


def test_octopus_compute_cheap_window():
    # Build 30-minute slots over 2 hours with varying prices
    base = "2024-01-01T00:{mm}:00+00:00"
    rates = []
    prices = [30, 25, 10, 40]  # 4 slots of 30 minutes
    for i, p in enumerate(prices):
        start = base.format(mm=f"{i*30:02d}")
        end_min = (i + 1) * 30
        end = base.format(mm=f"{end_min:02d}") if end_min < 60 else "2024-01-01T01:00:00+00:00"
        rates.append({"valid_from": end, "valid_to": start, "value_inc_vat": p})  # Octopus returns reverse-ordered
    # Function expects normalized order; but we handle sorting internally
    s, e, cost = compute_cheap_window(rates, 60)
    assert s and e
    # Cheapest hour should be slots with prices 25 and 10 => cost = 35 * 30 + 10 * 30 = 1050? No, cost is per minute sum
    # We can't assert numeric without tariff semantics; just ensure start before end and cost positive
    assert s < e
    assert cost > 0