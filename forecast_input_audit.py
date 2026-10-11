"""Audit independent forecast inputs against saved quotes; never trigger orders or paper fills."""
import csv, datetime, html, json, math, pathlib
ROOT=pathlib.Path(__file__).parent
DATA=ROOT/"data"; DOCS=ROOT/"docs"
def read_csv(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf-8") as fh:return list(csv.DictReader(fh))
def check_forecast(row,quotes,now):
    ticker=(row.get("ticker") or "").strip()
    source=(row.get("forecast_source") or "").strip()
    reason=(row.get("reason") or "").strip()
    result={"ticker":ticker,"source":source,"classification":"BLOCKED_RESEARCH_ONLY",
            "reason":"","gross_yes_edge_cents":None,"gross_no_edge_cents":None,
            "illustrative_net_yes_edge_cents":None,"illustrative_net_no_edge_cents":None}
    if not ticker or not source or not reason:
        result["reason"]="Missing ticker, independently documented source or rationale";return result
    try:
        timestamp=datetime.datetime.fromisoformat(row["forecast_utc"].replace("Z","+00:00"))
        p=float(row["yes_probability"])
        if timestamp.tzinfo is None or not math.isfinite(p) or not 0<p<1:
            raise ValueError("Invalid timestamp or probability")
    except (KeyError,ValueError,TypeError):
        result["reason"]="Invalid probability or timezone-aware forecast timestamp";return result
    age=(now-timestamp).total_seconds()
    if age<0 or age>7200:
        result["reason"]="Forecast outside 2-hour contemporaneous window";return result
    quote=quotes.get(ticker)
    if not quote:
        result["reason"]="No matching filtered public quote in scan snapshot";return result
    try:
        ya=float(quote["yes_ask_cents"]);na=float(quote["no_ask_cents"])
        close=datetime.datetime.fromisoformat(quote["close_time"].replace("Z","+00:00"))
        if not(all(math.isfinite(v) for v in (ya,na)) and 0<ya<100 and 0<na<100 and close>now):
            raise ValueError("Invalid quote or closed market")
    except (KeyError,ValueError,TypeError):
        result["reason"]="Quote unavailable, invalid or market already closed";return result
    yes=p*100-ya;no=(1-p)*100-na
    result.update(gross_yes_edge_cents=round(yes,2),gross_no_edge_cents=round(no,2),
                  illustrative_net_yes_edge_cents=round(yes-3,2),
                  illustrative_net_no_edge_cents=round(no-3,2),
                  reason="Quote comparison only. Forecast calibration, exact settlement rules, fee exceptions, depth and executable price unverified.")
    return result
def main():
    now=datetime.datetime.now(datetime.timezone.utc)
    forecasts=read_csv(DATA/"forecasts.csv")
    quotes={r["ticker"]:r for r in read_csv(DATA/"latest_markets.csv") if r.get("ticker")}
    audited=[check_forecast(r,quotes,now) for r in forecasts]
    report={"generated_utc":now.isoformat(),"submitted_forecasts":len(forecasts),
            "illustrative_comparisons":sum(r["gross_yes_edge_cents"] is not None for r in audited),
            "verified_signals":0,"enabled_for_paper_entries":False,
            "fee_assumption":"Illustrative 3 cents per contract, NOT a verified series fee or guaranteed fill",
            "safety_note":"Forecasts are user-supplied, not AI-created or independently validated. No expected-profit or trading signal claim.",
            "forecasts":audited}
    (DOCS/"forecast_input_audit.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    section='<section id="prediction-validation" style="padding:18px;border-radius:14px;background:#1c2c42;margin:20px 0"><h2>Prediction input audit</h2><p>'+str(len(forecasts))+' independently supplied forecasts; '+str(report["illustrative_comparisons"])+' preliminary quote comparisons; <strong>0 verified signals</strong>.</p><p>All entries remain research-only. A 3¢ fee estimate is illustrative; exchange rules, orderbook fills, and model calibration are not verified.</p><p><a href="./forecast_input_audit.json">View validation reasons and illustrative edge calculations</a></p></section>'
    dashboard=DOCS/"index.html"
    dashboard.write_text(dashboard.read_text(encoding="utf-8").replace("</body></html>",section+"</body></html>"),encoding="utf-8")
    print("Prediction input audit:",len(forecasts),"forecasts,",report["illustrative_comparisons"],"comparisons, no verified signals")
if __name__=="__main__":main()
