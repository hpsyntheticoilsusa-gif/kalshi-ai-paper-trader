"""Independent probabilistic WEATHER RESEARCH. Never place orders or auto-match Kalshi contracts."""
import csv,datetime,json,pathlib,urllib.parse,urllib.request,statistics
ROOT=pathlib.Path(__file__).parent
DATA=ROOT/"data";DATA.mkdir(exist_ok=True)
# Locations are research examples only. Model forecast is NOT settlement-station data.
CITIES=[("Salt Lake City, UT",40.7884,-111.9778,"America/Denver"),("New York City, NY",40.7789,-73.9692,"America/New_York"),("Chicago, IL",41.9742,-87.9073,"America/Chicago")]
FIELDS=["forecast_utc","city","target_date","ensemble_members","median_high_f","ensemble_highs_f","p_high_at_least_50f","p_high_at_least_60f","p_high_at_least_70f","p_high_at_least_80f","p_high_at_least_90f","source","warning"]
def request(lat,lon,timezone):
    options={"latitude":lat,"longitude":lon,"hourly":"temperature_2m","models":"gfs_seamless","forecast_days":3,"timezone":timezone}
    url="https://ensemble-api.open-meteo.com/v1/ensemble?"+urllib.parse.urlencode(options)
    req=urllib.request.Request(url,headers={"User-Agent":"KalshiPaperResearch/1.0"})
    with urllib.request.urlopen(req,timeout=40) as r:return json.load(r)
def evaluate(name,lat,lon,zone):
    payload=request(lat,lon,zone)
    hourly=payload["hourly"]
    dates=[str(x)[:10] for x in hourly["time"]]
    tomorrow=(datetime.date.fromisoformat(dates[0])+datetime.timedelta(days=1)).isoformat()
    indexes=[i for i,d in enumerate(dates) if d==tomorrow]
    if len(indexes)<20:raise ValueError("Insufficient hourly forecast coverage")
    keys=[k for k,v in hourly.items() if k.startswith("temperature_2m_member") and isinstance(v,list)]
    if len(keys)<10:raise ValueError("Too few ensemble members")
    highs=[]
    for key in keys:
        samples=[hourly[key][i] for i in indexes]
        if any(v is None for v in samples):continue
        highs.append(max(float(v)*9/5+32 for v in samples))
    if len(highs)<10:raise ValueError("Too few complete ensemble members")
    def probability(threshold):return round(sum(h>=threshold for h in highs)/len(highs),4)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    return dict(forecast_utc=now,city=name,target_date=tomorrow,ensemble_members=len(highs),median_high_f=round(statistics.median(highs),1),ensemble_highs_f=json.dumps([round(h,2) for h in highs]),p_high_at_least_50f=probability(50),p_high_at_least_60f=probability(60),p_high_at_least_70f=probability(70),p_high_at_least_80f=probability(80),p_high_at_least_90f=probability(90),source="Open-Meteo GFS ensemble hourly temperature_2m; daily maximum of hourly members",warning="Research only: uncalibrated model; not NWS settlement-station value; no Kalshi contract mapped")
def main():
    output=[];failures=[]
    for city,lat,lon,zone in CITIES:
        try:output.append(evaluate(city,lat,lon,zone))
        except Exception as exc:failures.append(city+": "+str(exc))
    if not output:raise RuntimeError("Weather ensemble research unavailable: "+"; ".join(failures))
    with (DATA/"weather_research.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(output)
    print("Weather research observations:",len(output),"failures:",len(failures))
    if failures:print("City fetch failures:",failures)
if __name__=="__main__":main()
