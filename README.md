# Kalshi paper-trading research lab

This repository runs an hourly **read-only market scanner** and publishes a mobile-friendly watchlist.

**No order placement, real-money trading, secrets, or broker account connections.**

## What is automated
- Fetch public Kalshi markets and filter by volume and indicative spreads.
- Publish a dashboard using GitHub Pages.
- Evaluate **independently supplied, timestamped forecasts** from `data/forecasts.csv`.
- Record paper entries for forecasts with a conservative estimated margin; check settlement on later runs.

## What is NOT automated
- AI has **not** independently forecast event probabilities.
- A paper entry is **not proof of an executable fill**. Order book depth, latency and exact fee schedule must be verified before a serious performance study.
- The fee assumption in the journal is **3 cents per contract total** for illustration, not a quoted Kalshi fee.

## How to add a forecast from your phone
Edit `data/forecasts.csv` on GitHub. Fields:

`ticker,yes_probability,forecast_utc,forecast_source,reason`

Example format (NOT a recommended trade):

`TEST-TICKER,0.64,2026-10-08T17:00:00Z,Independent source name,Documented model and evidence`

Entries must name a real active Kalshi ticker, include independently justified probability and source, be no older than 2 hours, and precede market close. The engine only considers an entry if after estimated fees its estimated edge is at least 8 percentage points. One position max per ticker. Do not fabricate sources or historical timestamps.

GitHub Actions > 'Scan Kalshi paper markets' > Run workflow starts a manual scan. Scheduled scans are hourly but can be delayed.

## Public visibility
This repository and its GitHub Pages site are public: do not enter private account information, passwords, API tokens, or investment account data. Results are research, not investment advice.

## Independent weather research (new)

The cloud workflow now runs `weather_research.py`, pulling GFS ensemble forecasts for Salt Lake City, New York City, and Chicago. It records tomorrow's estimated high temperature and example threshold probabilities in [`data/weather_research.csv`](data/weather_research.csv). These are **uncalibrated weather-model probabilities**, not LLM-generated signals and not verified against Kalshi settlement rules. No Kalshi contracts are auto-matched or paper traded by this module. Before any market-linked simulation, verify the exact observation station, reported statistic, market range boundaries, cutoff time, model calibration, and costs. If the weather source is unavailable the workflow may fail rather than show invented predictions.

## Weather research audit upgrade

`weather_audit.py` records timestamped contract-price/forecast observations in `data/weather_history.csv`, retaining a rolling 30-day window. It calculates **illustrative** one-contract taker fees using the general Kalshi fee formula; it does not check series-specific fee exceptions or orderbook fills. **These observations are not paper trades.** Calibration and exact station/date/contract-rule verification have NOT been completed, so automatic paper entry from weather research remains disabled. Only after forward-logged predictions are compared with exact official settlement observations should performance be claimed. Public repository files show all recorded research.
