"""Rank saved Kalshi snapshots for manual research. Never predicts probability or places trades."""
import csv, datetime, html, json, math, pathlib
ROOT=pathlib.Path(__file__).parent
DATA=ROOT/"data"; DOCS=ROOT/"docs"
def rank(row, now):
    try:
        yes=float(row["yes_ask_cents"]); no=float(row["no_ask_cents"])
        spread=float(row["spread_cents"]); volume=float(row["volume_24h"])
        closing=datetime.datetime.fromisoformat(row["close_time"].replace("Z","+00:00"))
        hours=(closing-now).total_seconds()/3600
    except (KeyError, ValueError, TypeError, OverflowError):
        return None
    if not all(math.isfinite(x) for x in (yes,no,spread,volume,hours)):
        return None
    if not(0<yes<100 and 0<no<100 and 0<=spread<=8 and volume>=100 and hours>0):
        return None
    # Transparent heuristic, NOT forecast edge. Penalize costly two-sided asks and near-close markets.
    friction=max(0,yes+no-100)
    liquidity=min(40,round(10*math.log10(max(1,volume)/100),2))
    tightness=round(30*(8-spread)/8,2)
    quote_quality=round(20*max(0,1-friction/12),2)
    time_score=10 if hours>=24 else (5 if hours>=3 else 0)
    score=round(liquidity+tightness+quote_quality+time_score,2)
    return {**row,"research_priority_score":score,"ask_sum_cents":round(yes+no,2),
            "two_ask_friction_cents":round(friction,2),"hours_to_close":round(hours,1),
            "research_only":True,"forecast_edge_verified":False,"fill_verified":False,
            "rank_basis":"24h volume, indicative YES spread, two-sided ask friction, time to close"}
def main():
    now=datetime.datetime.now(datetime.timezone.utc)
    with (DATA/"latest_markets.csv").open(newline="",encoding="utf-8") as fh:
        rows=list(csv.DictReader(fh))
    ranked=[x for row in rows if (x:=rank(row,now)) is not None]
    ranked.sort(key=lambda x:(-x["research_priority_score"],-float(x["volume_24h"]),x["ticker"]))
    report={"generated_utc":now.isoformat(),"eligible_for_trading":0,
            "ranking_type":"RESEARCH_PRIORITY_NOT_PREDICTED_EDGE",
            "scanned_filtered_markets":len(rows),"ranked_markets":len(ranked),
            "warning":"Indicative snapshot only. No independently validated forecast, orderbook depth, executable fill, calibrated edge, or verified fee schedule. Higher rank does NOT imply profitable trade.",
            "method":"Score up to 100: volume 0-40; YES spread 0-30; two-sided ask friction 0-20; hours to close 0-10. Informational sorting only.",
            "markets":ranked[:100]}
    (DOCS/"research_priority.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    def e(v):return html.escape(str(v))
    cards="".join('<article class="market"><div class="tag">Research priority '+e(x["research_priority_score"])+'/100 · NOT a signal</div><strong>'+e(x["title"])+'</strong><p class="ticker">'+e(x["ticker"])+'</p><p>24h volume '+e(int(float(x["volume_24h"])))+' · YES spread '+e(x["spread_cents"])+'¢ · YES/NO asks '+e(x["yes_ask_cents"])+'¢ / '+e(x["no_ask_cents"])+'¢ · time to close '+e(x["hours_to_close"])+'h</p></article>' for x in ranked[:12])
    section='<section id="research-ranking" style="padding:18px;border-radius:14px;background:#1c2c42;margin:20px 0"><h2>Research priority watchlist</h2><p>Top markets for manual investigation by liquidity, indicative spread, asking-price friction and time remaining. <strong>NOT recommendations or validated trading edges.</strong> No probability forecast, fee-adjusted expected value, orderbook depth, or executable fill is established.</p><p>'+str(len(ranked))+' ranked markets from '+str(len(rows))+' previously filtered market snapshots.</p><div class="cards">'+cards+'</div><p><a href="./research_priority.json">View transparent scores and full top-100 research list</a></p></section>'
    page=DOCS/"index.html"
    page.write_text(page.read_text(encoding="utf-8").replace("</body></html>",section+"</body></html>"),encoding="utf-8")
    print("Research priority:",len(ranked),"markets; NO validated trade signals")
if __name__=="__main__": main()
