"""Evaluate independently entered forecasts, log paper entries, settle via Kalshi public API. Never trade."""
import csv,json,urllib.request,urllib.parse,pathlib,datetime,math,collections
ROOT=pathlib.Path(__file__).parent; DATA=ROOT/"data";DATA.mkdir(exist_ok=True)
NOW=datetime.datetime.now(datetime.timezone.utc)
FIELDS=["ticker","side","forecast_probability","ask_cents","quantity","entry_utc","source","rationale","market_close","status","result","net_pnl_cents","estimated_fees_cents"]
def rows(path):
    with path.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def write(path,fields,items):
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(items)
def market(ticker):
    url="https://external-api.kalshi.com/trade-api/v2/markets/"+urllib.parse.quote(ticker,safe="")
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"PaperResearchScanner/1.0"}),timeout=25) as r:return json.load(r)["market"]
def numeric(m,k):
    v=m.get(k+"_dollars")
    if v is not None:return round(float(v)*100,3)
    v=m.get(k)
    return float(v) if v is not None else None
START_CENTS=100000
MAX_POSITION_CENTS=500
MAX_OPEN_CENTS=10000
def cost(x):
    return float(x["ask_cents"])*int(x["quantity"])+float(x["estimated_fees_cents"])
def settlement_pnl(x,result):
    return round((100*int(x["quantity"]) if result==x["side"] else 0)-cost(x),3)
def metrics(journal):
    settled=[x for x in journal if x["status"]=="SETTLED"]
    opened=[x for x in journal if x["status"]=="OPEN"]
    pnl=sum(float(x["net_pnl_cents"]) for x in settled)
    risk=sum(cost(x) for x in opened)
    wins=sum(x["result"]==x["side"] for x in settled)
    return {"paper_trades":len(journal),"settled_trades":len(settled),"wins":wins,"losses":len(settled)-wins,
            "estimated_paper_net_pnl_cents":round(pnl,3),"available_cash_cents":round(START_CENTS+pnl-risk,3),
            "open_risk_cents":round(risk,3),"realized_bankroll_cents":round(START_CENTS+pnl,3),
            "settled_brier":round(sum((float(x["forecast_probability"])-(x["result"]==x["side"]))**2 for x in settled)/len(settled),5) if settled else None}
def quantity_for(price,depth,cash,risk):
    if not all(math.isfinite(x) for x in (price,depth,cash,risk)):return 0
    return max(0,min(math.floor(depth),math.floor(min(MAX_POSITION_CENTS,cash,MAX_OPEN_CENTS-risk)/(price+3))))
def run():
    fpath=DATA/"forecasts.csv"; jpath=DATA/"paper_trades.csv"
    forecasts=rows(fpath) if fpath.exists() else []
    journal=rows(jpath) if jpath.exists() else []
    existing={x["ticker"]+"|"+x["side"]+"|"+x["forecast_utc"] if "forecast_utc" in x else x["ticker"]+"|"+x["side"]+"|"+x["entry_utc"] for x in journal}
    # No fabricated probabilities: only independently authored, timestamped forecasts.
    for f in forecasts:
        ticker=f.get("ticker","").strip();source=f.get("forecast_source","").strip();reason=f.get("reason","").strip()
        issued=f.get("forecast_utc","").strip()
        if not ticker or not source or not reason or not issued:continue
        try:
            t=datetime.datetime.fromisoformat(issued.replace("Z","+00:00"))
            p=float(f.get("yes_probability",""))
            if t.tzinfo is None or t>NOW or (NOW-t).total_seconds()>7200 or not .01<=p<=.99:continue
        except (ValueError,TypeError):continue
        # Conservative policy: no duplicate positions per ticker, no retrospective signals.
        if any(x["ticker"]==ticker for x in journal):continue
        try:
            m=market(ticker)
            if m.get("status") not in ("active","open"):continue
            close=datetime.datetime.fromisoformat(m["close_time"].replace("Z","+00:00"))
            if close<=NOW+datetime.timedelta(hours=1):continue
            occurrence=m.get("occurrence_datetime")
            if occurrence and datetime.datetime.fromisoformat(occurrence.replace("Z","+00:00"))<=NOW:continue
            yes=numeric(m,"yes_ask");no=numeric(m,"no_ask")
            options=[("yes",p,yes),("no",1-p,no)]
            # Simple conservative fees estimate (not an exact Kalshi fee quote): 3 cents / contract round trip.
            eligible=[(s,prob,price,prob*100-price-3) for s,prob,price in options if price is not None and 1<=price<=99]
            if not eligible:continue
            side,prob,price,ev=max(eligible,key=lambda x:x[3])
            if ev<8:continue
            depth=float(m.get(side+"_ask_size_fp") or 0)
            state=metrics(journal)
            qty=quantity_for(price,depth,state["available_cash_cents"],state["open_risk_cents"])
            if qty<1:continue
            journal.append({"ticker":ticker,"side":side,"forecast_probability":round(prob,4),"ask_cents":price,"quantity":qty,"entry_utc":NOW.isoformat(),"source":source,"rationale":reason,"market_close":m["close_time"],"status":"OPEN","result":"","net_pnl_cents":"","estimated_fees_cents":3*qty})
        except (OSError,KeyError,ValueError,TimeoutError) as e:
            print("Skipped forecast",ticker,type(e).__name__)
    for x in journal:
        if x["status"]!="OPEN":continue
        try:
            m=market(x["ticker"])
            # Only settle confirmed terminal market outcomes.
            if m.get("status") not in ("finalized",):continue
            result=str(m.get("result","")).lower()
            if result not in ("yes","no"):continue
            win=result==x["side"]
            entry=float(x["ask_cents"]);fees=float(x["estimated_fees_cents"])
            x.update(status="SETTLED",result=result,net_pnl_cents=settlement_pnl(x,result))
        except (OSError,KeyError,ValueError,TimeoutError) as e:
            print("Settlement deferred",x["ticker"],type(e).__name__)
    write(jpath,FIELDS,journal)
    settled=[x for x in journal if x["status"]=="SETTLED"]
    statuspath=DATA/"status.json"
    state=json.loads(statuspath.read_text()) if statuspath.exists() else {}
    state.update(metrics(journal),forecast_inputs=len(forecasts),note="Experimental forecast-led paper simulations. Assumed 3c per contract; displayed depth is not a guaranteed fill; series fee exceptions unverified.")
    statuspath.write_text(json.dumps(state,indent=2),encoding="utf-8")
    print("Paper journal:",len(journal),"entries,",len(settled),"settled")
if __name__=="__main__":run()
