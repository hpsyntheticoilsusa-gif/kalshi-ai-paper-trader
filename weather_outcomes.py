"""Resolve observed contract outcomes and score prospective probability forecasts.
Research scores, NOT paper fills/trades. No credentials or trading actions.
"""
import csv, json, datetime, pathlib, urllib.request, urllib.parse, time
ROOT=pathlib.Path(__file__).parent
DATA=ROOT/"data";DOCS=ROOT/"docs"
SOURCE=DATA/"weather_history.csv"; DEST=DATA/"weather_outcomes.csv"
FIELDS=["first_observed_utc","ticker","city","target_date","predicted_yes_probability","yes_ask_cents","no_ask_cents","market_status","result","checked_utc","brier_score","research_only"]
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
        if ticker in oldmap and oldmap[ticker].get("result") in ("yes","no"):continue
        try:
            m=market(ticker)
            status=str(m.get("status") or "")
            result=str(m.get("result") or "").lower()
            # A reported result may be provisional until finalization.
            confirmed=(status=="finalized" and result in ("yes","no"))
            p=float(record["rough_p_yes"])
            if not (0<=p<=1):continue
            oldmap[ticker]=dict(first_observed_utc=record["scan_utc"],ticker=ticker,city=record["city"],target_date=record["target_date"],predicted_yes_probability=p,yes_ask_cents=record["yes_ask_cents"],no_ask_cents=record["no_ask_cents"],market_status=status,result=result if confirmed else "",checked_utc=now,brier_score=round((p-(1 if result=="yes" else 0))**2,5) if confirmed else "",research_only="YES - uncalibrated weather model; no fill or validated settlement station")
        except Exception as e:
            errors+=1
            print("Skipped settlement check:",ticker,type(e).__name__)
        time.sleep(0.12)
    results=sorted(oldmap.values(),key=lambda x:(x["target_date"],x["ticker"]))
    with DEST.open("w",newline="",encoding="utf-8") as h:
        w=csv.DictWriter(h,fieldnames=FIELDS);w.writeheader();w.writerows(results)
    finished=[r for r in results if r["result"] in ("yes","no")]
    brier=sum(float(r["brier_score"]) for r in finished)/len(finished) if finished else None
    statusfile=DATA/"status.json"
    status=json.loads(statusfile.read_text()) if statusfile.exists() else {}
    status.update(outcomes_checked=len(results),outcomes_finalized=len(finished),weather_brier_score=round(brier,4) if brier is not None else None,weather_outcome_errors=errors,weather_validation="Exploratory only: station/window/rounding and calibration not verified; correlated contracts are NOT independent observations")
    statusfile.write_text(json.dumps(status,indent=2),encoding="utf-8")
    dashboard=DOCS/"index.html"
    if dashboard.exists():
        page=dashboard.read_text(encoding="utf-8")
        section='<section style="padding:16px;background:#24344a;border-radius:12px;margin:20px 0"><h2>Forecast outcomes</h2><p>'+str(len(finished))+' finalized contracts from '+str(len(results))+' distinct researched contracts. Mean Brier score: '+(str(round(brier,4)) if brier is not None else 'Not available yet')+'.</p><p>Research quality only; overlapping weather contracts are correlated. No verified trading profits or simulated fills.</p><p><a style="color:#a6d2ff" href="https://github.com/hpsyntheticoilsusa-gif/kalshi-ai-paper-trader/blob/main/data/weather_outcomes.csv">View results</a></p></section>'
        dashboard.write_text(page.replace("</body></html>",section+"</body></html>"),encoding="utf-8")
    print("Outcome checks:",len(results),"finalized:",len(finished),"errors:",errors)
if __name__=="__main__":main()
