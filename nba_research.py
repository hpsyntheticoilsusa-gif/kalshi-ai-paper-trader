"""NBA research inputs: independent NBA schedule feed + Kalshi market snapshots.
No probability estimates or trading signals until event matching and backtesting are validated.
"""
import csv,datetime,html,json,pathlib,urllib.request
ROOT=pathlib.Path(__file__).parent;DATA=ROOT/"data";DOCS=ROOT/"docs"
URL="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
def main():
    with (DATA/"latest_markets.csv").open(newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
    markets=[r for r in rows if (r.get("ticker") or "").upper().startswith("KXNBA")]
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    games=[];source_ok=False
    try:
        req=urllib.request.Request(URL,headers={"User-Agent":"KalshiPaperResearch/1.0","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=20) as response: raw=json.load(response)
        for event in raw.get("events",[]):
            comp=(event.get("competitions") or [{}])[0]
            teams=[]
            for item in comp.get("competitors",[]):
                team=item.get("team") or {}
                teams.append({"team":team.get("displayName"),"abbreviation":team.get("abbreviation"),"home_away":item.get("homeAway"),"score":item.get("score")})
            games.append({"event_id":str(event.get("id","")),"date":event.get("date"),"name":event.get("name"),"status":(event.get("status") or {}).get("type",{}).get("name"),"teams":teams})
        source_ok=True
    except Exception as exc:
        print("NBA independent scoreboard unavailable:",type(exc).__name__)
    # Do not associate individual Kalshi contracts with ESPN games using only fuzzy names.
    payload={"generated_utc":now,"independent_feed_available":source_ok,
             "independent_source":"ESPN public NBA scoreboard (not a settlement authority)",
             "qualifying_nba_markets":len(markets),"scoreboard_games":games,"market_samples":markets[:40],
             "validation_status":"RESEARCH_ONLY_NO_PROBABILITIES",
             "missing":["Verified contract-to-game mapping","Same-day data timestamps","Historical game dataset","Out-of-sample calibration","Kalshi market-specific resolution rules","Fees and executable orderbook depth"]}
    (DOCS/"nba_research.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    esc=lambda x:html.escape(str(x),quote=True)
    rows_html="".join("<article class='market'><strong>"+esc(g["name"])+"</strong><p>"+esc(g["date"])+" · "+esc(g["status"])+"</p></article>" for g in games[:12])
    if not rows_html:rows_html="<p>No independent NBA game schedule available from this scan. No synthetic matchups generated.</p>"
    section="<section id='nba-research' style='background:#24344a;border-radius:12px;padding:18px;margin:18px 0'><h2>NBA research lab (Step 12A)</h2><p>Qualifying NBA contracts: "+str(len(markets))+". Independent NBA scoreboard: "+("available" if source_ok else "unavailable")+". Games returned: "+str(len(games))+".</p><p style='color:#ffd184'><b>RESEARCH ONLY:</b> No validated NBA probabilities, forecasts, or paper-trade recommendations yet. Public game information is NOT proof of Kalshi contract settlement.</p><p>Next: verify event mapping and build/test a historical model before calculating any advantage.</p><div class='cards'>"+rows_html+"</div><p><a href='./nba_research.json'>View NBA research data</a></p></section>"
    page=DOCS/"index.html"
    if not page.exists():raise RuntimeError("Dashboard not generated")
    page.write_text(page.read_text(encoding="utf-8").replace("</body></html>",section+"</body></html>"),encoding="utf-8")
    print("NBA research:",len(markets),"qualifying contracts,",len(games),"independent games,feed",source_ok)
if __name__=="__main__":main()
