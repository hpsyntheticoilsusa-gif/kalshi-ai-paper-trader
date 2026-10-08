"""Resolve observed contract outcomes and score prospective probability forecasts.
Research scores, NOT paper fills/trades. No credentials or trading actions.
"""
import csv, json, datetime, pathlib, urllib.request, urllib.parse, time
ROOT=pathlib.Path(__file__).parent
DATA=ROOT/"data";DOCS=ROOT/"docs"
SOURCE=DATA/"weather_history.csv"; DEST=DATA/"weather_outcomes.csv"
FIELDS=["first_observed_utc","ticker","city","target_date","predicted_yes_probability","market_reference_probability","yes_ask_cents","no_ask_cents","market_status","result","checked_utc","brier_score","market_brier_score","research_only"]
def load(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf-8") as h:return list(csv.DictReader(h))
def market(ticker):
    path=urllib.parse.quote(ticker,safe="")
    req=urllib.request.Request("https://external-api.kalshi.com/trade-api/v2/markets/"+path,headers={"Accept":"application/json","User-Agent":"KalshiWeatherPaperLab/1.0"})
    with urllib.request.urlopen(req,timeout=25) as response:return json.load(response)["market"]
def main():
    old=load(DEST); oldmap={r["ticker"]:r for r in old}
    observations=load(SOURCE)
    first={}
    for r in sorted(observations,key=lambda x:x["scan_utc"]):
        first.setdefault(r["ticker"],r)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    errors=0
    for ticker,record in first.items():
        if ticker in oldmap and oldmap[ticker].get("result") in ("yes","no") and oldmap[ticker].get("market_brier_score") not in ("",None):continue
        try:
            m=market(ticker)
            status=str(m.get("status") or "")
            result=str(m.get("result") or "").lower()
            # A reported result may be provisional until finalization.
            confirmed=(status=="finalized" and result in ("yes","no"))
            p=float(record["rough_p_yes"])
            ya=float(record["yes_ask_cents"]); na=float(record["no_ask_cents"])
            if not (0<=p<=1 and 0<=ya<=100 and 0<=na<=100 and ya+na>0):continue
            # Normalized two-sided ask is a rough price-based benchmark, not a fair-probability quote.
            benchmark=ya/(ya+na)
            realized=1 if result=="yes" else 0
            oldmap[ticker]=dict(first_observed_utc=record["scan_utc"],ticker=ticker,city=record["city"],target_date=record["target_date"],predicted_yes_probability=p,market_reference_probability=round(benchmark,5),yes_ask_cents=record["yes_ask_cents"],no_ask_cents=record["no_ask_cents"],market_status=status,result=result if confirmed else "",checked_utc=now,brier_score=round((p-realized)**2,5) if confirmed else "",market_brier_score=round((benchmark-realized)**2,5) if confirmed else "",research_only="YES - uncalibrated weather model; no fill or validated settlement station")
        except Exception as e:
            errors+=1
            print("Skipped settlement check:",ticker,type(e).__name__)
        time.sleep(0.12)
    results=sorted(oldmap.values(),key=lambda x:(x["target_date"],x["ticker"]))
    with DEST.open("w",newline="",encoding="utf-8") as h:
        w=csv.DictWriter(h,fieldnames=FIELDS);w.writeheader();w.writerows(results)
    # Phone-readable finalized outcomes only. Never expose provisional results.
    settled=[{"ticker":r["ticker"],"result":r["result"],"market_status":"finalized","checked_utc":r["checked_utc"]}
             for r in results if r.get("market_status")=="finalized" and r.get("result") in ("yes","no")]
    (DOCS/"settlements.json").write_text(json.dumps({"generated_utc":now,"settlements":settled},indent=2),encoding="utf-8")
    finished=[r for r in results if r["result"] in ("yes","no")]
    brier=sum(float(r["brier_score"]) for r in finished)/len(finished) if finished else None
    market_brier=sum(float(r["market_brier_score"]) for r in finished)/len(finished) if finished else None
    statusfile=DATA/"status.json"
    status=json.loads(statusfile.read_text()) if statusfile.exists() else {}
    status.update(outcomes_checked=len(results),outcomes_finalized=len(finished),weather_brier_score=round(brier,4) if brier is not None else None,market_reference_brier_score=round(market_brier,4) if market_brier is not None else None,weather_outcome_errors=errors,weather_validation="Exploratory only: station/window/rounding and calibration not verified; correlated contracts are NOT independent observations")
    statusfile.write_text(json.dumps(status,indent=2),encoding="utf-8")
    dashboard=DOCS/"index.html"
    if dashboard.exists():
        page=dashboard.read_text(encoding="utf-8")
        section='<section style="padding:16px;background:#24344a;border-radius:12px;margin:20px 0"><h2 id="forecast-results">Forecast outcomes</h2><p>'+str(len(finished))+' finalized contracts from '+str(len(results))+' distinct researched contracts. Mean Brier score: '+(str(round(brier,4)) if brier is not None else 'Not available yet')+'. Market reference Brier score: '+(str(round(market_brier,4)) if market_brier is not None else 'Not available yet')+'. Lower is better.</p><p>Research quality only; overlapping weather contracts are correlated. No verified trading profits or simulated fills.</p><p><a style="color:#a6d2ff" href="https://github.com/hpsyntheticoilsusa-gif/kalshi-ai-paper-trader/blob/main/data/weather_outcomes.csv">View results</a></p></section>'
        dashboard.write_text(page.replace("</body></html>",section+"</body></html>"),encoding="utf-8")
    print("Outcome checks:",len(results),"finalized:",len(finished),"errors:",errors)
if __name__=="__main__":main()
