# BTC Race 24h — Crash-Rebound Dip Buyer

A long-only trading bot for cbBTC/USDC on 1-minute bars. It does one thing:
buy sharp selloffs and ride the rebound, then get out.

## How it trades

The bot answers every batch of incoming bars with orders (or none at all).
It stays flat in cash most of the time and only enters when the market has
just fallen hard and is already bouncing back.

**Entry (full size, one position, all cash in):**
- The price has dropped at least 2.0% over the last 60 minutes.
- The latest bar's close is at least 0.1% above the 60-bar low — that is the
  bounce confirmation. No bounce, no trade.

**Exit (whichever comes first):**
- Trailing stop: 1.0% below the highest close since entry.
- Hard stop: 98.8% of the entry cost — a strict floor, no second chances.
- Max hold: 180 bars (3 hours). Old positions do not linger.

There are no shorts, no leverage, and no second position while one is open.

## Economics — stated honestly

Fills happen at the next bar's open, not at the signal price. Every trade
pays 4 bps in fees plus 2 bps in slippage, plus constant-product price impact
against the pool. A round trip therefore costs roughly 0.5% before any price
move, so the strategy only makes sense on sharp selloffs: it trades a few
times per day at most and sits in cash the rest of the time. A quiet market
means no trades, and that is by design.

## Run locally

The entry point is `main.py` (Python 3.13, standard library only — no
dependencies to install). To grade it against the kit, from the unpacked
kit directory run:

```sh
node cli/makefun.mjs grade-local --kit <kit> --bot <repo> --driver docker
```

Replace `<kit>` with the kit directory and `<repo>` with this repository.
A hello from the bot on startup just means it loaded cleanly and is ready
for its first batch of bars.

## License

MIT — see `LICENSE`.
