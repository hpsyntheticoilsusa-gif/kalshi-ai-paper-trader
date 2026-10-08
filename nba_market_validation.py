"""Archive timestamped NBA quote snapshots for future model-vs-market validation.
Research only: NO predicted edges or synthetic fills. No game mapping assumed.
"""
import csv,datetime,json,pathlib,math,html
ROOT=pathlib.Path(__file__).parent;DATA=ROOT/"data";DOCS=ROOT/"docs"
SOURCE=DATA/"latest_markets.csv"
DEST=DATA/"nba_quote_history.csv"
FIELDS=["scan_utc","ticker","event_ticker","title","yes_ask_cents","no_ask_cents","spread_cents","volume_24h","close_time","status"]
def load(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def valid(r):
    try:
        ya=float(r["yes_ask_cents"]);na=float(r["no_ask_cents"]);sp=float(r["spread_cents"]);volume=float(r["volume_24h"])
        return all(math.isfinite(n) for n in (ya,na,sp,volume)) and 0<ya<100 and 0<na<100 and 0<=sp<=8 and volume>=100
    except (TypeError,ValueError,KeyError):return False
def main():
    now=datetime.datetime.now(datetime.timezone.utc)
    scan=now.isoformat()
    past=load(DEST)
    fresh=[]
    for r in load(SOURCE):
        if not (r.get("ticker") or "").upper().startswith("KXNBA") or not valid(r):continue
        fresh.append({k:(scan if k=="scan_utc" else "OBSERVATION_ONLY" if k=="status" else r.get(k,"")) for k in FIELDS})
    cutoff=(now-datetime.timedelta(days=30)).isoformat()
    # Keep one observation per ticker per scan; rolling 30 days. Not an orderbook.
    unique={(r["scan_utc"],r["ticker"]):r for r in past+fresh if r.get("scan_utc","")>=cutoff and r.get("ticker")}
    records=sorted(unique.values(),key=lambda r:(r["scan_utc"],r["ticker"]))
    DATA.mkdir(exist_ok=True)
    with DEST.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction="ignore");w.writeheader();w.writerows(records)
    events=len({r["event_ticker"] for r in records if r.get("event_ticker")})
    report={"generated_utc":scan,"observations":len(records),"new_observations":len(fresh),"distinct_events":events,
       "first_snapshot_utc":records[0]["scan_utc"] if records else None,
       "last_snapshot_utc":records[-1]["scan_utc"] if records else None,
       "verified_contract_to_game_matches":0,"validated_expected_edge_count":0,
       "status":"OBSERVATION_ONLY",
       "warnings":["24h market volume and indicative asks are not proof of executable liquidity.",
                   "Game outcomes and exact settlement rules not matched to market tickers.",
                   "Historical quote archive starts when this module is activated; past prices cannot be reconstructed from current quotes.",
                   "No Kalshi profitability, calibration or edge can be computed yet."]}
    (DOCS/"nba_market_validation.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    block="<section style='background:#24344a;border-radius:12px;padding:18px;margin:18px 0'><h2>NBA market-price validation (Step 12F)</h2><p>Timestamped NBA quote snapshots: "+str(len(records))+"; new in this scan: "+str(len(fresh))+"; distinct events: "+str(events)+".</p><p>Verified contract-to-game matches: 0. Validated expected-edge signals: 0.</p><p style='color:#ffd184'>OBSERVATION ONLY — we are collecting contemporaneous prices for later testing. No verified resolution mapping, trade fills, or profitable model edge. Historical quotes cannot be backfilled retroactively.</p><p><a href='./nba_market_validation.json'>View validation status</a></p></section>"
    dash=DOCS/"index.html"
    if not dash.exists():raise RuntimeError("Dashboard missing")
    dash.write_text(dash.read_text(encoding="utf-8").replace("</body></html>",block+"</body></html>"),encoding="utf-8")
    print("NBA quote observations:",len(records),"new:",len(fresh),"events:",events)
if __name__=="__main__":main()
