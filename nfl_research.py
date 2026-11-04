"""NFL contract reconnaissance: observations only, never trade instructions.

Reads the existing, liquidity-filtered Kalshi snapshot. Does not infer win
probabilities from prices, match events by fuzzy names, or manufacture fills.
"""
import csv
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
UTC = dt.timezone.utc

def classify(ticker):
    t = (ticker or "").upper()
    if not t.startswith("KXNFL"):
        return None
    # Require explicit known prefixes; a generic "game" match is unsafe.
    if t.startswith(("KXNFLGAME-", "KXNFLWINNER-", "KXNFLMATCH-")):
        return "POTENTIAL_GAME_WINNER_UNVERIFIED"
    if t.startswith("KXNFLOT-"):
        return "OVERTIME"
    if t.startswith(("KXNFLTD-", "KXNFLFIRSTTD-", "KXNFLPASSTDS-", "KXNFLTDPROT-")):
        return "TOUCHDOWN_PROP"
    if t.startswith(("KXNFL1H", "KXNFL1Q")):
        return "PARTIAL_GAME"
    return "OTHER_NFL_CONTRACT"

def inspect(rows, now=None):
    now = now or dt.datetime.now(UTC)
    found = []
    for row in rows:
        ticker = str(row.get("ticker") or "").strip()
        kind = classify(ticker)
        if not kind:
            continue
        close = row.get("close_time", "")
        try:
            parsed = dt.datetime.fromisoformat(close.replace("Z", "+00:00"))
            future = parsed.tzinfo is not None and parsed > now
        except (ValueError, TypeError, AttributeError):
            future = False
        found.append({
            "ticker": ticker,
            "title": row.get("title", ""),
            "event_ticker": row.get("event_ticker", ""),
            "contract_type": kind,
            "yes_ask_cents": row.get("yes_ask_cents"),
            "no_ask_cents": row.get("no_ask_cents"),
            "close_time": close,
            "future_close": future,
            "signal": "PASS",
            "independent_probability": None,
            "validated_net_edge": None,
            "paper_quantity": 0,
            "reason": "No verified NFL model, contract-specific settlement mapping, executable fill depth and fee schedule.",
        })
    found.sort(key=lambda r: (r["contract_type"], r["ticker"]))
    return found

def main():
    with (DATA / "latest_markets.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    matches = inspect(rows)
    counts = {}
    for item in matches:
        kind = item["contract_type"]
        counts[kind] = counts.get(kind, 0) + 1
    report = {
        "generated_utc": dt.datetime.now(UTC).isoformat(),
        "scope": "Existing liquidity-filtered scanner snapshot, not all NFL contracts",
        "scanned_saved_markets": len(rows),
        "nfl_contracts_found": len(matches),
        "by_contract_type": counts,
        "verified_game_winner_matches": 0,
        "qualified_picks": 0,
        "paper_orders_created": 0,
        "status": "OBSERVATION_ONLY",
        "missing": [
            "Verified live game-winner market taxonomy and exact mapping",
            "Independent, timestamped and calibrated pregame win probabilities",
            "Contract-specific settlement rules and outcome sources",
            "Fresh executable quotes, fill depth and applicable fees",
        ],
        "contracts": matches,
    }
    DOCS.mkdir(exist_ok=True)
    (DOCS / "nfl_research.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("NFL research:", len(matches), "contracts; 0 validated trades (PASS)")
    return report

if __name__ == "__main__":
    main()
