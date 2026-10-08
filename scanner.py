"""Read-only Kalshi market scanner: NO trading credentials or order placement."""
import csv, json, html, pathlib, datetime, urllib.request, urllib.parse, time
ROOT=pathlib.Path(__file__).parent
DATA=ROOT/"data"; DOCS=ROOT/"docs"
DATA.mkdir(exist_ok=True); DOCS.mkdir(exist_ok=True)
NOW=datetime.datetime.now(datetime.timezone.utc)
BASE="https://external-api.kalshi.com/trade-api/v2"
def fetch(path, params):
    url=BASE+path+"?"+urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"PaperResearchScanner/1.0","Accept":"application/json"}),timeout=30) as response:
                return json.load(response)
        except Exception:
            if attempt==2: raise
            time.sleep(2**attempt)
def cents(m, key):
    value=m.get(key+"_dollars")
    if value is not None:
        try: return round(float(value)*100,3)
        except (TypeError,ValueError): return None
    value=m.get(key)
    try: return float(value) if value is not None else None
    except (TypeError,ValueError): return None
def main():
    raw=[]; cursor=None
    for i in range(4):
        opts={"limit":1000,"status":"open","mve_filter":"exclude"}
        if cursor: opts["cursor"]=cursor
        result=fetch("/markets",opts)
        raw.extend(result.get("markets",[]))
        cursor=result.get("cursor")
        if not cursor: break
    if not raw: raise RuntimeError("No markets returned; refusing to overwrite report")
    items=[]
    for m in raw:
        ya,yb,na,nb=[cents(m,k) for k in ("yes_ask","yes_bid","no_ask","no_bid")]
        if ya is None and nb is not None: ya=100-nb
        if na is None and yb is not None: na=100-yb
        try: volume=float(m.get("volume_24h_fp") or m.get("volume_24h") or 0)
        except (TypeError,ValueError): volume=0
        spread=ya-yb if ya is not None and yb is not None else None
        if not (ya is not None and na is not None and spread is not None and 1<=ya<=99 and 1<=na<=99 and 0<=spread<=8 and volume>=100): continue
        items.append({"ticker":m.get("ticker",""),"title":m.get("title",""),"event_ticker":m.get("event_ticker",""),"yes_ask_cents":ya,"no_ask_cents":na,"spread_cents":round(spread,2),"volume_24h":volume,"close_time":m.get("close_time","")})
    items.sort(key=lambda x:(-x["volume_24h"],x["spread_cents"]))
    fields=["ticker","title","event_ticker","yes_ask_cents","no_ask_cents","spread_cents","volume_24h","close_time"]
    with (DATA/"latest_markets.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(items[:500])
    status={"last_scan_utc":NOW.isoformat(),"fetched":len(raw),"passing_filters":len(items),"paper_trades":0,"note":"Screening only. No AI forecasts, simulated fills, or real trading."}
    (DATA/"status.json").write_text(json.dumps(status,indent=2),encoding="utf-8")
    def cell(v): return html.escape(str(v))
    categorize=lambda m: "Sports / esports" if any(k in (m["ticker"]+" "+m["event_ticker"]).upper() for k in ("GAME","MATCH","NBA","NFL","MLB","CS2","DOTA","EUROLEAGUE","UFC","TENNIS")) else "Other markets"
    table="".join("<article class=\"market\"><div class=\"tag\">"+cell(categorize(m))+"</div><strong>"+cell(m["title"])+"</strong><p class=\"ticker\">"+cell(m["ticker"])+"</p><div class=\"prices\"><span>YES ask <b>"+cell(m["yes_ask_cents"])+"¢</b></span><span>NO ask <b>"+cell(m["no_ask_cents"])+"¢</b></span><span>Spread <b>"+cell(m["spread_cents"])+"¢</b></span><span>24h vol <b>"+cell(int(m["volume_24h"]))+"</b></span></div></article>" for m in items[:75])
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Kalshi Paper Scanner</title><link rel="manifest" href="./manifest.webmanifest"><meta name="theme-color" content="#101827"><link rel="icon" type="image/png" href="./icon-192.png"><link rel="apple-touch-icon" href="./icon-192.png"><style>body{background:#101827;color:#f1f5fd;font:16px system-ui;margin:0 auto;max-width:1100px;padding:18px}p{color:#bfcce0}table{border-collapse:collapse;min-width:680px;width:100%}th,td{padding:10px;border-bottom:1px solid #39465d;text-align:left}.scroll{overflow-x:auto}.stats{display:flex;gap:12px;flex-wrap:wrap}.tile{background:#24344a;border-radius:12px;padding:16px;flex:1;min-width:130px}.tile strong{display:block;font-size:28px}.warning{border-left:4px solid orange;padding:12px;background:#2b3343}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:12px}.market{background:#24344a;border-radius:12px;padding:14px;min-width:0}.market strong{display:block}.ticker{font-size:11px;overflow-wrap:anywhere}.prices{display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px}.prices span{padding:8px;background:#17253a;border-radius:6px}.prices b{display:block;font-size:18px}.tag{color:#a0d0ff;font-size:12px;margin-bottom:8px}a{color:#a0d0ff}</style></head><body><h1>Kalshi Paper Market Scanner</h1><p>Scan: '''+cell(NOW.strftime("%Y-%m-%d %H:%M UTC"))+'''</p><div class="warning"><b>Research-only weather ensemble model active; no validated trade signals or paper fills.</b><p>Forecast probabilities are uncalibrated, weather settlement rules have not been verified, and market quotes do not guarantee fills.</p></div><div class="stats"><div class="tile">Markets scanned<strong>'''+str(len(raw))+'''</strong></div><div class="tile">Passing filters<strong>'''+str(len(items))+'''</strong></div></div><div class="tile"><strong style="font-size:17px">Paper Trade Simulator</strong><p>Practice placing a hypothetical order using our saved research prices. Nothing is sent to Kalshi. Tickets are stored only in your browser.</p><p><a href="paper-ticket.html" style="display:inline-block;padding:12px 16px;border-radius:10px;background:#36d576;color:#092010;font-weight:700;text-decoration:none">Open paper ticket →</a></p></div><div class="tile"><strong style="font-size:17px">Research status</strong><p>Weather forecasts and contract comparisons are running. Outcome scoring begins after markets finalize. No verified profitable trades.</p><p><a href="#weather-research">Weather research ↓</a> | <a href="#forecast-results">Forecast outcomes ↓</a></p></div><details><summary style="padding:16px 0;font-weight:bold;font-size:20px;cursor:pointer">Show market watchlist (optional)</summary><h2>Market watchlist</h2><p><b>Paper trades:</b> recorded separately in <a href="https://github.com/hpsyntheticoilsusa-gif/kalshi-ai-paper-trader/blob/main/data/paper_trades.csv">GitHub paper journal</a>. No eligible paper trade forecasts have been entered yet.</p><p>24h volume ≥100 and indicative YES spread ≤8¢.</p><div class="cards">'''+table+'''</div></details></body></html>'''
    (DOCS/"index.html").write_text(page,encoding="utf-8")
    print("Scan completed:",len(raw),"markets,",len(items),"passed")
if __name__=="__main__": main()
