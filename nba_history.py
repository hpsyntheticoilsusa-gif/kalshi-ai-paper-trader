"""NBA historical results and strictly prior-game baseline audit; research only."""
import datetime,json,pathlib,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).parent;DOCS=ROOT/"docs";DATA=ROOT/"data"
HISTORY=DATA/"nba_games_history.json"
DAILY_BATCH=28
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
    try:kind=int(kind)
    except (ValueError,TypeError):kind=None
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
    # Up to 28 distinct historical dates each run. Revisit recent dates only once caught up.
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
    histories={}; tested=[]; elo={}; elo_tested=[]
    for day in sorted({(g.get("date") or "")[:10] for g in regular}):
        daily=[g for g in regular if (g.get("date") or "")[:10]==day]
        for g in daily:
            home=histories.get(g["home"]["id"],[])
            away=histories.get(g["away"]["id"],[])
            if len(home)>=5 and len(away)>=5:
                p=max(.05,min(.95,.5+.55*((sum(home[-5:])+1)/7-(sum(away[-5:])+1)/7)))
                tested.append({"game_id":g["id"],"date":g["date"],"predicted_home_win":round(p,4),"actual_home_win":g["home_win"],"brier":round((p-g["home_win"])**2,5)})
            if len(home)>=10 and len(away)>=10:
                eh=elo.get(g["home"]["id"],1500);ea=elo.get(g["away"]["id"],1500)
                p_elo=1/(1+10**((ea-eh-65)/400))
                elo_tested.append({"game_id":g["id"],"date":g["date"],"predicted_home_win":round(p_elo,4),"actual_home_win":g["home_win"],"brier":round((p_elo-g["home_win"])**2,5)})
        changes={}
        for g in daily:
            hid=g["home"]["id"];aid=g["away"]["id"]
            eh=elo.get(hid,1500);ea=elo.get(aid,1500)
            delta=16*(g["home_win"]-1/(1+10**((ea-eh-65)/400)))
            changes[hid]=changes.get(hid,0)+delta
            changes[aid]=changes.get(aid,0)-delta
        for tid,delta in changes.items():elo[tid]=elo.get(tid,1500)+delta
        for g in daily:
            histories.setdefault(g["home"]["id"],[]).append(g["home_win"])
            histories.setdefault(g["away"]["id"],[]).append(1-g["home_win"])
    # Fair comparison: only the identical game IDs scored by BOTH models.
    by_form={t["game_id"]:t for t in tested}
    by_elo={t["game_id"]:t for t in elo_tested}
    common=sorted(set(by_form)&set(by_elo))
    paired_form=sum(by_form[k]["brier"] for k in common)/len(common) if common else None
    paired_elo=sum(by_elo[k]["brier"] for k in common)/len(common) if common else None
    # Chronological holdout: last 20% of the common-game timeline.
    # This is a diagnostic split only: model parameters were chosen previously.
    ordered_common=sorted(common,key=lambda k:(by_elo[k]["date"],k))
    split=max(1,int(len(ordered_common)*.8)) if ordered_common else 0
    held=ordered_common[split:]
    holdout={"games":len(held),"form_brier":round(sum(by_form[k]["brier"] for k in held)/len(held),4) if held else None,
             "elo_brier":round(sum(by_elo[k]["brier"] for k in held)/len(held),4) if held else None,
             "neutral_brier":.25 if held else None,
             "first_game_date":by_elo[held[0]]["date"] if held else None}
    reliability=[]
    for low in (0,.2,.4,.6,.8):
        high=low+.2
        subset=[by_elo[k] for k in held if low<=by_elo[k]["predicted_home_win"]<(high if high<1 else 1.000001)]
        n=len(subset)
        reliability.append({"bin":str(round(low,1))+"-"+str(round(high,1)),
                            "games":n,"mean_predicted":round(sum(x["predicted_home_win"] for x in subset)/n,3) if n else None,
                            "actual_home_win_rate":round(sum(x["actual_home_win"] for x in subset)/n,3) if n else None})
    model=sum(t["brier"] for t in tested)/len(tested) if tested else None
    elo_brier=sum(t['brier'] for t in elo_tested)/len(elo_tested) if elo_tested else None
    phases={phase:sum(g.get("season_type")==phase for g in games) for phase in ("preseason","regular","postseason","unknown")}
    out={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "source":"ESPN public scoreboard; not Kalshi settlement source",
         "historical_dates_checked":len(checked),"historical_dates_target":len(days),
         "dates_requested_this_run":len(chosen),"failed_daily_fetches":failed,
         "completed_games":len(games),"by_phase":phases,"backtest_games":len(tested),
         "model_brier":round(model,4) if model is not None else None,
         "neutral_50_50_brier":.25 if tested else None,
         "paired_backtest_games":len(common),"chronological_holdout":holdout,"elo_holdout_calibration":reliability,
         "paired_form_brier":round(paired_form,4) if paired_form is not None else None,
         "paired_elo_brier":round(paired_elo,4) if paired_elo is not None else None,
         "historical_backfill_complete":len(checked)>=len(days),
         "elo_backtest_games":len(elo_tested),"elo_brier":round(elo_brier,4) if elo_brier is not None else None,
         "status":"EXPLORATORY_NOT_VALIDATED",
         "warning":"Regular-season-only strictly chronological simple form model, with backfill potentially incomplete. No market odds, injuries, opponent adjustments, game matching or validated profitability.",
         "examples":tested[-20:],"elo_examples":elo_tested[-20:]}
    (DOCS/"nba_history.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    def score(v):return "Not available" if v is None else str(v)
    block="<section style='background:#24344a;border-radius:12px;padding:18px;margin:18px 0'><h2>NBA history and backtesting (Step 12C)</h2><p>Historical dates checked: "+str(len(checked))+"/"+str(len(days))+". Completed games: "+str(len(games))+" (regular: "+str(phases["regular"])+", preseason: "+str(phases["preseason"])+", postseason: "+str(phases["postseason"])+"). Chronological regular-season test games: "+str(len(tested))+".</p><p>Model Brier: "+score(out["model_brier"])+". Neutral 50/50 baseline: "+score(out["neutral_50_50_brier"])+". Fixed-parameter Elo backtest: "+str(len(elo_tested))+" games, Brier "+score(out["elo_brier"])+". Lower is better.</p><p style='color:#ffd184'>RESEARCH ONLY. Historical backfill may be incomplete and the model is not calibrated or validated against actual Kalshi fills.</p><p><a href='./nba_history.json'>View historical audit</a></p></section>"
    block+="<section style='background:#24344a;border-radius:12px;padding:18px;margin:18px 0'><h2>NBA matched-game comparison (Step 12E)</h2><p>Games evaluated by both models: "+str(len(common))+". Recent-form Brier on matched games: "+score(out["paired_form_brier"])+". Elo Brier on matched games: "+score(out["paired_elo_brier"])+". 50/50 benchmark: "+score(.25 if common else None)+". Lower is better.</p><p style='color:#ffd184'>"+("Historical dates fully checked; model validation still pending." if len(checked)>=len(days) else "HISTORICAL BACKFILL INCOMPLETE: "+str(len(checked))+" of "+str(len(days))+" dates checked.")+" These are exploratory scores, not demonstrated profitability or calibrated win probabilities.</p></section>"
    hold_brier=lambda v:"Not available" if v is None else str(v)
    block+="<section style='background:#24344a;border-radius:12px;padding:18px;margin:18px 0'><h2>NBA chronological holdout (Step 12J)</h2><p>Later matched games: "+str(holdout["games"])+". Elo Brier: "+hold_brier(holdout["elo_brier"])+". Recent-form Brier: "+hold_brier(holdout["form_brier"])+". Neutral benchmark: "+hold_brier(holdout["neutral_brier"])+". Lower is better.</p><p style='color:#ffd184'>DIAGNOSTIC ONLY: parameters were previously chosen and these historical games may have influenced prior development. This is not a pristine unseen-data or live-market validation; no profitable signal is verified.</p></section>"
    rows="".join("<tr><td>"+bucket["bin"]+"</td><td>"+str(bucket["games"])+"</td><td>"+hold_brier(bucket["mean_predicted"])+"</td><td>"+hold_brier(bucket["actual_home_win_rate"])+"</td></tr>" for bucket in reliability)
    block+="<section style='background:#24344a;border-radius:12px;padding:18px;margin:18px 0'><h2>NBA Elo probability calibration (Step 12K)</h2><p>Later-game diagnostic only ("+str(len(held))+" games). Compare prediction ranges with actual home-team wins.</p><div style='overflow-x:auto'><table><thead><tr><th>Probability</th><th>Games</th><th>Avg forecast</th><th>Actual wins</th></tr></thead><tbody>"+rows+"</tbody></table></div><p style='color:#ffd184'>Small bins are unstable; these results are not an untouched validation set and do not establish a trading edge. No NBA live signals permitted.</p></section>"
    page=DOCS/"index.html"
    if not page.exists():raise RuntimeError("Dashboard missing")
    page.write_text(page.read_text(encoding="utf-8").replace("</body></html>",block+"</body></html>"),encoding="utf-8")
    print("NBA history:",len(checked),"days,",len(games),"games,",len(tested),"tests, errors",failed)
if __name__=="__main__":main()
