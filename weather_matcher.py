"""Conservative WEATHER contract discovery. Outputs REVIEW candidates; never auto enters paper trades."""
import csv,datetime,json,pathlib,re,urllib.request,urllib.parse
ROOT=pathlib.Path(__file__).parent;DATA=ROOT/"data";DOCS=ROOT/"docs"
BASE="https://external-api.kalshi.com/trade-api/v2"
SERIES={"Salt Lake City, UT":"KXHIGHSLC","New York City, NY":"KXHIGHNY","Chicago, IL":"KXHIGHCHI"}
COLS=["scan_utc","city","ticker","market_title","target_date","series_ticker","strike_type","floor_strike","cap_strike","yes_ask_cents","no_ask_cents","median_high_f","rough_yes_probability","rough_edge_yes_cents","rough_edge_no_cents","status","review_reason","settlement_rules_verified","forecast_matches_resolution_source","model_calibrated","fees_and_depth_verified","eligible_signal"]
def get(path,params=None):
    url=BASE+path+("?"+urllib.parse.urlencode(params) if params else "")
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"PaperWeatherResearch/1.0","Accept":"application/json"}),timeout=30) as r:return json.load(r)
def money(m,key):
    try:
        v=m.get(key+"_dollars")
        return round(float(v)*100,2) if v is not None else (float(m[key]) if m.get(key) is not None else None)
    except (ValueError,TypeError):return None
def prob(highs,m):
    kind=m.get("strike_type")
    a=m.get("floor_strike");b=m.get("cap_strike")
    try:a=float(a) if a is not None else None;b=float(b) if b is not None else None
    except (ValueError,TypeError):return None
    if kind=="greater" and a is not None:return sum(h>a for h in highs)/len(highs)
    if kind=="less" and b is not None:return sum(h<b for h in highs)/len(highs)
    if kind=="between" and a is not None and b is not None:return sum(a<=h<=b for h in highs)/len(highs)
    return None
def main():
    weather=DATA/"weather_research.csv"
    if not weather.exists():raise RuntimeError("Missing weather research; no candidates produced")
    with weather.open(newline="",encoding="utf-8") as f:forecasts=list(csv.DictReader(f))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    candidates=[]
    for f in forecasts:
        series=SERIES.get(f["city"])
        if not series:continue
        # Hourly modeled highs are not station-observed settlement highs.
        # Without ensemble highs, do not invent event-range probabilities.
        try:highs=json.loads(f.get("ensemble_highs_f",""))
        except (ValueError,TypeError):continue
        if len(highs)<10:continue
        try:markets=get("/markets",{"series_ticker":series,"status":"open","limit":200}).get("markets",[])
        except Exception as e:
            print("Discovery unavailable for",series,type(e).__name__);continue
        date=f["target_date"]
        for m in markets:
            # Cross-check explicit event date from the canonical YYYY-MON-DD event ticker.
            et=m.get("event_ticker","")
            stamp=re.search(r"-(\d{2})([A-Z]{3})(\d{2})(?:$|-)",et)
            if not stamp:continue
            try:
                market_date=datetime.datetime.strptime("20"+stamp.group(1)+stamp.group(2)+stamp.group(3),"%Y%b%d").date().isoformat()
            except ValueError:continue
            if market_date!=date:continue
            p=prob(highs,m)
            if p is None:continue
            ya=money(m,"yes_ask");na=money(m,"no_ask")
            if ya is None or na is None:continue
            why="BLOCKED: exact contract/date settlement source and observation window unverified; GFS hourly highs not matched to settlement product; probability uncalibrated; fee/depth and fill unverified"
            candidates.append(dict(scan_utc=now,city=f["city"],ticker=m.get("ticker",""),market_title=m.get("title",""),target_date=date,series_ticker=series,strike_type=m.get("strike_type"),floor_strike=m.get("floor_strike"),cap_strike=m.get("cap_strike"),yes_ask_cents=ya,no_ask_cents=na,median_high_f=f.get("median_high_f"),rough_yes_probability=round(p,4),rough_edge_yes_cents=round(p*100-ya,2),rough_edge_no_cents=round((1-p)*100-na,2),status="RESEARCH_ONLY_NO_TRADE",review_reason=why,settlement_rules_verified=False,forecast_matches_resolution_source=False,model_calibrated=False,fees_and_depth_verified=False,eligible_signal=False))
    candidates.sort(key=lambda r:max(r["rough_edge_yes_cents"],r["rough_edge_no_cents"]),reverse=True)
    # Published research snapshots for the LOCAL-ONLY ticket. These are not executable exchange quotes.
    (DOCS/"candidates.json").write_text(json.dumps(candidates[:100],ensure_ascii=False),encoding="utf-8")
    with (DATA/"weather_candidates.csv").open("w",newline="",encoding="utf-8") as o:
        w=csv.DictWriter(o,fieldnames=COLS);w.writeheader();w.writerows(candidates)
    # Escaped presentation; separate from the auto paper trade journal.
    import html
    def esc(x):return html.escape(str(x))
    cards="".join('<article style="background:#25354a;padding:14px;border-radius:12px;margin:12px 0"><strong>'+esc(x["city"])+' — '+esc(x["market_title"])+'</strong><p>'+esc(x["ticker"])+'</p><p>Rough YES probability: '+esc(round(x["rough_yes_probability"]*100,1))+'% | YES ask '+esc(x["yes_ask_cents"])+'¢ | NO ask '+esc(x["no_ask_cents"])+'¢</p><p>Raw gross edge (YES/NO): '+esc(x["rough_edge_yes_cents"])+'¢ / '+esc(x["rough_edge_no_cents"])+'¢</p><p style="color:#ffd184">BLOCKED — not a validated signal; settlement and model checks pending</p></article>' for x in candidates[:20])
    summary='<section style="padding:16px;border-radius:12px;background:#142034;color:white"><h2 id="weather-research">Weather contract research</h2><p>Potential contract matches: '+str(len(candidates))+'. None qualify as validated signals. Settlement rules, station-specific forecasts, probability calibration, fees, and usable orderbook depth remain unverified; apparent edges are gross theoretical comparisons, not expected profit. Station and settlement-time mismatch can reverse an apparent edge.</p>'+cards+'</section>'
    page=DOCS/"index.html"
    if page.exists():
        current=page.read_text(encoding="utf-8")
        current=current.replace("</body></html>",summary+"</body></html>")
        page.write_text(current,encoding="utf-8")
    print("Weather contract review candidates:",len(candidates))
if __name__=="__main__":main()
