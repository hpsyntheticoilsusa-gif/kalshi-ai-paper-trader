"""Append-only-by-key research history, fee estimates, and unverified settlement status."""
import csv,datetime,math,pathlib,json,html
DATA=pathlib.Path(__file__).parent/"data"; DOCS=pathlib.Path(__file__).parent/"docs"
HISTORY=DATA/"weather_history.csv"
FIELDS=["scan_utc","city","target_date","ticker","title","rough_p_yes","yes_ask_cents","no_ask_cents","estimated_yes_taker_fee_cents","estimated_no_taker_fee_cents","illustrative_yes_net_edge_cents","illustrative_no_net_edge_cents","status","validation"]
def read(p):
    if not p.exists():return []
    with p.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def fee(cents):
    # General Kalshi taker fee, ONE contract, rounded up to one whole cent.
    p=cents/100
    return math.ceil((0.07*p*(1-p))*100-1e-10)
def main():
    current=read(DATA/"weather_candidates.csv")
    history=read(HISTORY)
    keys={(r["scan_utc"],r["ticker"]) for r in history}
    fresh=[]
    for r in current:
        key=(r["scan_utc"],r["ticker"])
        if key in keys:continue
        ya=float(r["yes_ask_cents"]);na=float(r["no_ask_cents"]);p=float(r["rough_yes_probability"])
        fy=fee(ya);fn=fee(na)
        fresh.append(dict(scan_utc=r["scan_utc"],city=r["city"],target_date=r["target_date"],ticker=r["ticker"],title=r["market_title"],rough_p_yes=p,yes_ask_cents=ya,no_ask_cents=na,estimated_yes_taker_fee_cents=fy,estimated_no_taker_fee_cents=fn,illustrative_yes_net_edge_cents=round(100*p-ya-fy,2),illustrative_no_net_edge_cents=round(100*(1-p)-na-fn,2),status="OBSERVATION_ONLY",validation="UNVERIFIED station/window/rounding/calibration/orderbook; series-specific fees may vary"))
    history.extend(fresh)
    # Keep 30 days of hourly observations, to bound repo growth.
    cutoff=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=30)).isoformat()
    history=[r for r in history if r["scan_utc"]>=cutoff]
    with HISTORY.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(history)
    statusfile=DATA/"status.json"
    state=json.loads(statusfile.read_text()) if statusfile.exists() else {}
    state.update(weather_research_observations=len(history),new_weather_observations=len(fresh),verified_weather_signals=0,weather_paper_trades=0,forecast_calibration="NOT MEASURED: no verified station settlement observations collected")
    statusfile.write_text(json.dumps(state,indent=2),encoding="utf-8")
    dashboard=DOCS/"index.html"
    if dashboard.exists():
        page=dashboard.read_text(encoding="utf-8")
        block='<section style="padding:16px;background:#23334a;color:#fff;border-radius:12px;margin:18px 0"><h2>Research history & fees</h2><p>'+str(len(history))+' timestamped contract-price observations stored (rolling 30 days). '+str(len(fresh))+' new this scan. No verified trading signals, fills or completed calibration yet.</p><p>Estimated fee: general one-contract Kalshi taker formula with cent rounding; series exceptions not checked. Apparent edges are NOT executable returns. Weather dates, station and boundaries have not been verified.</p><p><a style="color:#a6d2ff" href="https://github.com/hpsyntheticoilsusa-gif/kalshi-ai-paper-trader/blob/main/data/weather_history.csv">View historical research CSV</a></p></section>'
        dashboard.write_text(page.replace("</body></html>",block+"</body></html>"),encoding="utf-8")
    print("Weather history saved:",len(history),"new observations:",len(fresh))
if __name__=="__main__":main()
