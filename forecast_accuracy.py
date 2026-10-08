"""Exploratory forecast accuracy report. Contract outcomes are NOT station-aligned ground truth."""
import csv, json, pathlib, datetime, html
ROOT=pathlib.Path(__file__).parent
DATA=ROOT/"data"; DOCS=ROOT/"docs"
def read(path):
    if not path.exists(): return []
    with path.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
def main():
    rows=read(DATA/"weather_outcomes.csv")
    finalized=[]
    for r in rows:
        if r.get("market_status")!="finalized" or r.get("result") not in ("yes","no"): continue
        try:
            p=float(r["predicted_yes_probability"]);m=float(r["market_reference_probability"])
            if not(0<=p<=1 and 0<=m<=1):continue
            finalized.append((r,p,m,int(r["result"]=="yes")))
        except (ValueError,TypeError,KeyError):continue
    # One deterministic representative contract per city/event-day. Related strike brackets are correlated.
    unique={}
    for r,p,m,y in sorted(finalized,key=lambda x:(x[0].get("first_observed_utc",""),x[0].get("ticker",""))):
        key=(r.get("city",""),r.get("target_date",""))
        unique.setdefault(key,(r,p,m,y))
    sample=list(unique.values())
    def score(index):
        return round(sum((v[index]-v[3])**2 for v in sample)/len(sample),4) if sample else None
    buckets=[]
    for low,high in [(0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.00001)]:
        b=[(p,y) for _,p,_,y in sample if low<=p<high]
        buckets.append({"range":f"{low:.0%}–{min(high,1):.0%}","count":len(b),"mean_predicted":round(sum(p for p,y in b)/len(b),3) if b else None,"observed_yes_rate":round(sum(y for p,y in b)/len(b),3) if b else None})
    report={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "finalized_contracts":len(finalized),"independent_city_days":len(sample),
       "model_brier":score(1),"rough_market_baseline_brier":score(2),
       "enough_data_for_conclusions":False,
       "minimum_city_days_for_preliminary_review":30,
       "caution":"Uncalibrated GFS hourly ensemble differs from Kalshi settlement stations/products. Market benchmark is normalized two-sided asks, not executable probability. City-days overlap across markets. Scores are exploratory, not a proven edge.",
       "reliability_bins":buckets}
    (DOCS/"forecast_accuracy.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    def display(v):return "Not available" if v is None else str(v)
    p='<section style="padding:16px;background:#21354b;border-radius:12px;margin:20px 0"><h2 id="forecast-accuracy">Forecast accuracy audit (Step 8B)</h2>'
    p+='<p>Finalized contracts: '+str(len(finalized))+'; representative city-days: '+str(len(sample))+'. Model Brier: '+display(report["model_brier"])+'; approximate market baseline Brier: '+display(report["rough_market_baseline_brier"])+'. Lower is better.</p>'
    p+='<p style="color:#ffd184">NOT VALIDATED: Fewer than 30 independent city-days, or station/product mismatch unresolved. No accuracy or profitability claim. This report is descriptive, NOT trained or calibrated.</p>'
    p+='<p>Raw ensemble forecast highs are not necessarily Kalshi’s designated settlement observations. Related contracts are correlated; one representative market per city-day is used for the overview.</p>'
    p+='<p><a style="color:#a6d2ff" href="./forecast_accuracy.json">View accuracy report and probability bins</a></p></section>'
    page=DOCS/"index.html"
    if page.exists():page.write_text(page.read_text(encoding="utf-8").replace("</body></html>",p+"</body></html>"),encoding="utf-8")
    print("Forecast accuracy audit:",len(finalized),"finalized contracts;",len(sample),"representative city-days")
if __name__=="__main__":main()
