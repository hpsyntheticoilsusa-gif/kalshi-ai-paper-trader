# Settlement source verification — 2026-10-08

**Mandatory research gate: do not auto-create weather paper trades.**

## Critical finding
The Kalshi Oct 8, 2026 Chicago KXHIGHCHI and New York KXHIGHNY market pages identify **The Weather Company** (Chicago CLIMDW, NYC CLINYC) as the resolution source. Other historical market pages refer to the National Weather Service's Climatological Report (Daily). Therefore, **settlement sources cannot be assumed based solely on the series ticker**.

- Chicago Oct 8: https://kalshi.com/markets/kxhighchi/highest-temperature-in-chicago/kxhighchi-26oct08
- NYC Oct 8: https://kalshi.com/markets/kxhighny/highest-temperature-in-nyc/kxhighny-26oct08
- Earlier example using NWS: https://kalshi.com/markets/KXHIGHCHI

## Checklist per actual contract/date
1. Retrieve and retain market-specific complete rules and named resolution source at forecast timestamp.
2. Confirm station/product identity (e.g., CLIMDW or CLINYC) and any specific time-zone/day boundary.
3. Validate integer temperature rounding and range inequality, including 2-degree ranges.
4. Produce aligned weather forecasts for exactly the same product/station/date. Open-Meteo hourly ensemble highs are NOT interchangeable with settlement-source maxima.
5. Collect multiple independent event-days and compare calibrated model score with contemporaneous benchmark; avoid counting overlapping brackets as independent.
6. Capture usable orderbook depth, current fees, and actual decision timestamp before any paper order/PNL simulation.
7. Keep unresolved comparisons OBSERVATION_ONLY; do not promote to signals merely because raw gross edge is high.

**October 9 status:** Exact Chicago/NY market rules not independently verified; treat every apparent edge as illustrative.
