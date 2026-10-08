"""NBA historical results and strictly prior-game baseline audit; research only."""
import datetime,json,pathlib,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).parent;DOCS=ROOT/"docs";DATA=ROOT/"data"
HISTORY=DATA/"nba_games_history.json"
DAILY_BATCH=14
BASE="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
def fetch(day):
    url=BASE+"?"+urllib.parse.urlencode({"dates":day.strftime("%Y%m%d"),"limit":100})
    req=urllib.request.Request(url,headers={"User-Agent":"KalshiPaperResearch/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=18) as h:return json.load(h)
def score_event(event):
    comp=(event.get("competitions") or [{}])[0]
    st=(event.get("status") or {}).get("type",{})
    if not st.get("completed"):return None
    teams=comp.get("competitors") or []
    if len(teams)!=2:return None
    result={}
    for t in teams:
        side=t.get("homeAway");tid=(t.get("team") or {}).get("id")
        try:pts=int(t["score"])
        except (ValueError,TypeError,KeyError):return None
        if side not in ("home","away") or not tid:return None
        result[side]={"id":str(tid),"name":(t.get("team") or {}).get("displayName",""),"points":pts}
    if len(result)!=2 or result["home"]["points"]==result["away"]["points"]:return None
    kind=(event.get("season") or {}).get("type")
    phase={1:"preseason",2:"regular",3:"postseason"}.get(kind,"unknown")
    return {"date":event.get("date"),"id":str(event.get("id","")),"season_type":phase,"home":result["home"],"away":result["away"],"home_win":int(result["home"]["points"]>result["away"]["points"])}
def main():
    today=datetime.datetime.now(datetime.timezone.utc).date()
    DATA.mkdir(exist_ok=True)
    archive={"checked_days":[],"games":[]}
    if HISTORY.exists():
        try:
            saved=json.loads(HISTORY.read_text(encoding="utf-8"))
            if isinstance(saved.get("checked_days"),list) and isinstance(saved.get("games"),list):
                archive=saved
        except (ValueError,AttributeError):
            pass
    first=datetime.date(today.year-1,10,1)
    if first>=today: first=datetime.date(today.year-2,10,1)
    checked=set(archive["checked_days"])
    days=[first+datetime.timedelta(days=i) for i in range((today-first).days)]
    pending=[day for day in days if day.isoformat() not in checked]
    # Up to 14 distinct historical dates each run. Revisit recent dates only once caught up.
    chosen=pending[:DAILY_BATCH] if pending else days[-3:]
    byid={g["id"]:g for g in archive["games"] if g.get("id")}
    failed=0
    for day in chosen:
        try:
            for ev in fetch(day).get("events",[]):
                game=score_event(ev)
                if game: byid[game["id"]]=game
            checked.add(day.isoformat())
        except Exception as err:
            failed+=1
            print("NBA history skipped:",day,type(err).__name__)
    games=sorted(byid.values(),key=lambda g:(g.get("date") or "",g["id"]))
    HISTORY.write_text(json.dumps({"checked_days":sorted(checked),"games":games},separators=(",",":")),encoding="utf-8")
    regular=[g for g in games if g.get("season_type")=="regular"]
    histories={}; tested=[]
    for day in sorted({(g.get("date") or "")[:10] for g in regular}):
        daily=[g for g in regular if (g.get("date") or "")[:10]==day]
        for g in daily:
            home=histories.get(g["home"]["id"],[])
            away=histories.get(g["away"]["id"],[])
            if len(home)<5 or len(away)<5:continue
            p=max(.05,min(.95,.5+.55*((sum(home[-5:])+1)/7-(sum(away[-5:])+1)/7)))
            tested.append({"game_id":g["id"],"date":g["date"],"predicted_home_win":round(p,4),"actual_home_win":g["home_win"],"brier":round((p-g["home_win"])**2,5)})
        for g in daily:
            histories.setdefault(g["home"]["id"],[]).append(g["home_win"])
            histories.setdefault(g["away"]["id"],[]).append(1-g["home_win"])
    model=sum(t["brier"] for t in tested)/len(tested) if tested else None
    phases={phase:sum(g.get("season_type")==phase for g in games) for phase in ("preseason","regular","postseason","unknown")}
    out={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "source":"ESPN public scoreboard; not Kalshi settlement source",
         "historical_dates_checked":len(checked),"historical_dates_target":len(days),
         "dates_requested_this_run":len(chosen),"failed_daily_fetches":failed,
         "completed_games":len(games),"by_phase":phases,"backtest_games":len(tested),
         "model_brier":round(model,4) if model is not None else None,
         "neutral_50_50_brier":.25 if tested else None,
         "status":"EXPLORATORY_NOT_VALIDATED",
         "warning":"Regular-season-only strictly chronological simple form model, with backfill potentially incomplete. No market odds, injuries, opponent adjustments, game matching or validated profitability.",
         "examples":tested[-20:]}
    (DOCS/"nba_history.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    def score(v):return "Not available" if v is None else str(v)
    block="<section style='background:#24344a;border-radius:12px;padding:18px;margin:18px 0'><h2>NBA history and backtesting (Step 12C)</h2><p>Historical dates checked: "+str(len(checked))+"/"+str(len(days))+". Completed games: "+str(len(games))+" (regular: "+str(phases["regular"])+", preseason: "+str(phases["preseason"])+", postseason: "+str(phases["postseason"])+"). Chronological regular-season test games: "+str(len(tested))+".</p><p>Model Brier: "+score(out["model_brier"])+". Neutral 50/50 baseline: "+score(out["neutral_50_50_brier"])+". Lower is better.</p><p style='color:#ffd184'>RESEARCH ONLY. Historical backfill may be incomplete and the model is not calibrated or validated against actual Kalshi fills.</p><p><a href='./nba_history.json'>View historical audit</a></p></section>"
    page=DOCS/"index.html"
    if not page.exists():raise RuntimeError("Dashboard missing")
    page.write_text(page.read_text(encoding="utf-8").replace("</body></html>",block+"</body></html>"),encoding="utf-8")
    print("NBA history:",len(checked),"days,",len(games),"games,",len(tested),"tests, errors",failed)
if __name__=="__main__":main()
