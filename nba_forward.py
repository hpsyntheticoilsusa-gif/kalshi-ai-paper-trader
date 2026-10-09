"""Prospective NBA Elo forecast ledger. Research only, never places trades."""
import json,csv,datetime,pathlib,math
ROOT=pathlib.Path(__file__).parent;DATA=ROOT/"data";DOCS=ROOT/"docs"
LEDGER=DATA/"nba_forward_predictions.csv"
FIELDS=["game_id","game_date","home_id","away_id","home_name","away_name","recorded_utc","raw_home_probability","result_home_win","scored_utc"]
def read_csv(p):
    if not p.exists():return []
    with p.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def main():
    now=datetime.datetime.now(datetime.timezone.utc)
    history=json.loads((DATA/"nba_games_history.json").read_text(encoding="utf-8")).get("games",[])
    research=json.loads((DOCS/"nba_research.json").read_text(encoding="utf-8"))
    current={r["game_id"]:r for r in read_csv(LEDGER)}
    # Ratings from COMPLETED regular-season games, never preseason.
    elo={};completed=sorted((g for g in history if g.get("season_type")=="regular"),key=lambda x:(x.get("date",""),x["id"]))
    for day in sorted({g.get("date","")[:10] for g in completed}):
        games=[g for g in completed if g.get("date","")[:10]==day]
        updates={}
        for g in games:
            h=g["home"]["id"];a=g["away"]["id"];rh=elo.get(h,1500);ra=elo.get(a,1500)
            p=1/(1+10**((ra-rh-65)/400))
            delta=16*(g["home_win"]-p)
            updates[h]=updates.get(h,0)+delta;updates[a]=updates.get(a,0)-delta
        for team,delta in updates.items():elo[team]=elo.get(team,1500)+delta
    new=0
    if research.get("independent_feed_available"):
        for g in research.get("scoreboard_games",[]):
            id_=str(g.get("event_id",""))
            if not id_ or id_ in current or g.get("status")!="STATUS_SCHEDULED":continue
            try:tip=datetime.datetime.fromisoformat(g["date"].replace("Z","+00:00"))
            except (ValueError,TypeError,KeyError):continue
            if not now<tip<=now+datetime.timedelta(days=3):continue
            teams={t.get("home_away"):t for t in g.get("teams",[])}
            # Scoreboard stored names/abbreviations but not ESPN IDs: do not guess.
            # Future predictions require stable team identifiers matched to historical IDs.
            if not teams.get("home",{}).get("team_id") or not teams.get("away",{}).get("team_id"):continue
            h=teams["home"];a=teams["away"]
            rh=elo.get(str(h["team_id"]),1500);ra=elo.get(str(a["team_id"]),1500)
            p=1/(1+10**((ra-rh-65)/400))
            current[id_]={"game_id":id_,"game_date":g["date"],"home_id":str(h["team_id"]),"away_id":str(a["team_id"]),"home_name":h["team"],"away_name":a["team"],"recorded_utc":now.isoformat(),"raw_home_probability":f"{p:.6f}","result_home_win":"","scored_utc":""}
            new+=1
    outcomes={str(g["id"]):g for g in history}
    scored=0
    for row in current.values():
        if row["result_home_win"]!="":continue
        result=outcomes.get(row["game_id"])
        if not result:continue
        try:
            recorded=datetime.datetime.fromisoformat(row["recorded_utc"])
            tip=datetime.datetime.fromisoformat(result["date"].replace("Z","+00:00"))
        except (ValueError,KeyError,TypeError):continue
        if recorded>=tip or row["home_id"]!=result["home"]["id"] or row["away_id"]!=result["away"]["id"]:continue
        row["result_home_win"]=str(result["home_win"]);row["scored_utc"]=now.isoformat();scored+=1
    DATA.mkdir(exist_ok=True)
    with LEDGER.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(sorted(current.values(),key=lambda x:x["recorded_utc"]))
    complete=[r for r in current.values() if r["result_home_win"] in ("0","1")]
    brier=sum((float(r["raw_home_probability"])-int(r["result_home_win"]))**2 for r in complete)/len(complete) if complete else None
    output={"generated_utc":now.isoformat(),"predictions_saved":len(current),"new_predictions":new,"scored_games":len(complete),"newly_scored":scored,"raw_elo_forward_brier":round(brier,4) if brier is not None else None,"status":"FORWARD_RESEARCH_ONLY","note":"Only strict pre-tipoff predictions scored against exact ESPN game IDs. No Kalshi market mapping, no trade signals. Unmatched games are skipped, never guessed."}
    (DOCS/"nba_forward_audit.json").write_text(json.dumps(output,indent=2),encoding="utf-8")
    block="<section style='background:#24344a;border-radius:12px;padding:18px;margin:18px 0'><h2>NBA forward prediction test (Step 12N)</h2><p>Predictions locked before games: "+str(len(current))+". Completed and scored: "+str(len(complete))+". Forward Brier: "+(str(round(brier,4)) if brier is not None else "Not available")+".</p><p style='color:#ffd184'>RESEARCH ONLY: Unmatched games are omitted; no contract predictions or verified trading advantage.</p><p><a href='./nba_forward_audit.json'>View forward-test status</a></p></section>"
    dashboard=DOCS/"index.html"
    dashboard.write_text(dashboard.read_text(encoding="utf-8").replace("</body></html>",block+"</body></html>"),encoding="utf-8")
    print("NBA forward:",len(current),"predictions,",len(complete),"scored,",new,"new")
if __name__=="__main__":main()
