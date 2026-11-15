"""BTC race bot: one asset, CBBTC priced in USDC.

The hello message starts the session, then the harness sends one batch
per bar and expects one reply with our orders for that batch. Each bar
carries a raw integer close at price_scale 5; we compare raw ints only
and never convert to dollars. All arithmetic is integer arithmetic.

Strategy, in short: while flat, wait for a >= 2.0% drop over 60 bars
that has bounced >= 0.1% off its 60-bar low, then buy all cash. While
holding, track the peak close since entry and sell the whole position
on a 1.0% trailing stop, a hard stop at 98.8% of cost, or after 180
bars held. No other orders are ever placed.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

# Every CBBTC close seen so far, oldest first, including warm-up bars.
_closes = []

# Entry tracking for the current position, or None while flat.
# entry_seq is the state.seq of the batch where the position first
# appeared; peak is the highest close seen since that entry.
_entry_seq = None
_peak = None


def on_batch(state, batch):
    """Return the orders for one batch of bars."""
    global _entry_seq, _peak

    close = state.close("CBBTC")
    if close is None:
        return []

    # Only record a close when this batch actually carries a fresh
    # CBBTC bar; state.close() repeats the latest close on a batch
    # with no fresh bar, which would append a stale duplicate.
    for bar in batch.get("bars") or []:
        if bar.get("symbol") == "CBBTC":
            _closes.append(int(bar["c"]))
            break

    # Never trade while warming up; closes are still recorded above.
    if state.warming_up:
        return []

    positions = state.positions or {}

    # Flat: look for the dip-and-bounce entry.
    if "CBBTC" not in positions:
        _entry_seq = None
        _peak = None
        if len(_closes) < 61:
            return []
        now = _closes[-1]
        then60 = _closes[-61]
        low60 = min(_closes[-61:])
        drop_enough = then60 * 100 >= now * 102
        bounced_off_low = now * 1000 >= low60 * 1001
        # Entry needs BOTH: now <= 98% of the close 60 bars ago, and
        # now >= 100.1% of the lowest close of the last 61 bars.
        # Never send a buy with no cash behind it.
        if state.cash <= 0:
            return []
        if drop_enough and bounced_off_low:
            return [
                {
                    "side": "buy",
                    "symbol": "CBBTC",
                    "notional_quote_units": state.cash,
                    "max_slippage_bps": 300,
                }
            ]
        return []

    # Holding: record entry tracking when the position first appears,
    # then update the peak with each new close.
    position = positions["CBBTC"]
    if _entry_seq is None:
        _entry_seq = state.seq
        _peak = close
    elif close > _peak:
        _peak = close

    cost = getattr(position, "cost_quote_units", None)
    if cost is None:
        cost = getattr(position, "cost", 0)

    trailing_stop = close * 100 <= _peak * 99
    hard_stop = state.value("CBBTC", position.qty) * 1000 <= cost * 988
    max_hold = state.seq - _entry_seq >= 180

    if trailing_stop or hard_stop or max_hold:
        # Do NOT clear _entry_seq/_peak here: if this sell is rejected
        # (e.g. max_slippage) the position is still open next batch and
        # the old peak must survive so the stop re-triggers immediately.
        # The flat branch above clears both once the position is gone.
        return [
            {
                "side": "sell",
                "symbol": "CBBTC",
                "qty": position.qty,
                "max_slippage_bps": 300,
            }
        ]
    return []


if __name__ == "__main__":
    makefun_bars.run(on_batch)
