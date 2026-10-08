"""NBA historical results and strictly prior-game baseline audit; research only."""
import datetime,json,pathlib,urllib.parse,urllib.request,html,math,statistics
ROOT=pathlib.Path(__file__).parent;DOCS=ROOT/"docs"
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
    return {"date":event.get("date"),"id":str(event.get("id","")),"home":result["home"],"away":result["away"],"home_win":int(result["home"]["points"]>result["away"]["points"])}
def main():
    today=datetime.datetime.now(datetime.timezone.utc).date()
    # Limited window deliberately avoids accumulating stale data and keeps hourly requests modest.
    days=[today-datetime.timedelta(days=n) for n in range(1,22)]
    byid={};failed=0
    for day in days:
        try:
            for ev in fetch(day).get("events",[]):
                g=score_event(ev)
                if g:byid[g["id"]]=g
        except Exception as err:
            failed+=1
            print("NBA history skipped:",day,type(err).__name__)
    games=sorted(byid.values(),key=lambda g:(g["date"] or "",g["id"]))
    prior={}
    tested=[]
    for g in games:
        h=prior.get(g["home"]["id"],[]);a=prior.get(g["away"]["id"],[])
        # Only games earlier than the current tipoff are used; no outcome leakage.
        if len(h)>=5 and len(a)>=5:
            ph=(sum(h[-5:])+1)/(len(h[-5:])+2)
            pa=(sum(a[-5:])+1)/(len(a[-5:])+2)
            # Heuristic probability: regularized recent win rates with mild home offset.
            p=max(.05,min(.95,.5+.55*(ph-pa)+.03))
            tested.append({"game_id":g["id"],"date":g["date"],"home_team":g["home"]["name"],"away_team":g["away"]["name"],"predicted_home_win":round(p,4),"actual_home_win":g["home_win"],"brier":round((p-g["home_win"])**2,5)})
        prior.setdefault(g["home"]["id"],[]).append(g["home_win"])
        prior.setdefault(g["away"]["id"],[]).append(1-g["home_win"])
    baseline=sum((.5-t["actual_home_win"])**2 for t in tested)/len(tested) if tested else None
    model=sum(t["brier"] for t in tested)/len(tested) if tested else None
    out={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source":"ESPN public scoreboard; not a Kalshi settlement source",
         "lookback_days":len(days),"failed_daily_fetches":failed,"completed_games":len(games),"backtest_games":len(tested),
         "model_brier":round(model,4) if model is not None else None,"neutral_50_50_brier":round(baseline,4) if baseline is not None else None,
         "status":"EXPLORATORY_NOT_VALIDATED","warning":"21-day rolling scoreboard only; limited samples and possible preseason games. No opponent-strength or injury modeling, no contract matching, no odds at decision time, no live game predictions. This is an illustrative historical baseline only.","examples":tested[-20:]}
    (DOCS/"nba_history.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    scores=lambda v:("Not available" if v is None else str(v))
    block="<section style='background:#24344a;border-radius:12px;padding:18px;margin:18px 0'><h2 id='nba-history'>NBA historical model audit (Step 12B)</h2><p>Completed games collected: "+str(len(games))+". Out-of-sample chronological examples: "+str(len(tested))+". Model Brier: "+scores(out["model_brier"])+". Neutral 50/50 benchmark: "+scores(out["neutral_50_50_brier"])+". Lower is better.</p><p style='color:#ffd184'>EXPERIMENTAL ONLY — short historical window, uncertain sample quality, preseason and regular-season not separated yet. No validated probabilities, market advantage, or paper-trading recommendation.</p><p><a href='./nba_history.json'>View NBA historical audit data</a></p></section>"
    page=DOCS/"index.html"
    if not page.exists():raise RuntimeError("Dashboard missing")
    page.write_text(page.read_text(encoding="utf-8").replace("</body></html>",block+"</body></html>"),encoding="utf-8")
    print("NBA history",len(games),"games,",len(tested),"chronological tests,",failed,"fetch failures")
if __name__=="__main__":main()
