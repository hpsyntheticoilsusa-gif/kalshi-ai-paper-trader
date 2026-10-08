"""Chronological NBA scoring baseline audit. Research-only, no Kalshi predictions."""
import json,pathlib,datetime,statistics
ROOT=pathlib.Path(__file__).parent; DATA=ROOT/"data"; DOCS=ROOT/"docs"
def main():
    source=DATA/"nba_games_history.json"
    games=json.loads(source.read_text()).get("games",[]) if source.exists() else []
    regular=sorted((g for g in games if g.get("season_type")=="regular"),key=lambda g:(g.get("date",""),g.get("id","")))
    histories={}; estimates=[]; prior_totals=[]
    for day in sorted({str(g.get("date",""))[:10] for g in regular}):
        daily=[g for g in regular if str(g.get("date",""))[:10]==day]
        for g in daily:
            home=g["home"];away=g["away"]
            h=histories.get(home["id"],[]);a=histories.get(away["id"],[])
            if len(h)<5 or len(a)<5:continue
            # Estimate each team's points scored as average offense and opponent concessions.
            hs=statistics.mean(x[0] for x in h[-5:]); ha=statistics.mean(x[1] for x in h[-5:])
            as_=statistics.mean(x[0] for x in a[-5:]); aa=statistics.mean(x[1] for x in a[-5:])
            expected_home=(hs+aa)/2;expected_away=(as_+ha)/2
            actual_home=home["points"];actual_away=away["points"]
            baseline_total=statistics.mean(prior_totals) if len(prior_totals)>=30 else None
            estimates.append({"baseline_margin":0.0,"baseline_total":round(baseline_total,2) if baseline_total is not None else None,"game_id":g["id"],"date":g["date"],
                "projected_margin":round(expected_home-expected_away,2),
                "actual_margin":actual_home-actual_away,
                "projected_total":round(expected_home+expected_away,2),
                "actual_total":actual_home+actual_away})
        for g in daily:
            home=g["home"];away=g["away"]
            prior_totals.append(home["points"]+away["points"])
            histories.setdefault(home["id"],[]).append((home["points"],away["points"]))
            histories.setdefault(away["id"],[]).append((away["points"],home["points"]))
    def mae(field,target):
        return round(sum(abs(x[field]-x[target]) for x in estimates)/len(estimates),2) if estimates else None
    paired=[x for x in estimates if x["baseline_total"] is not None]
    margin_base=round(sum(abs(x["actual_margin"]) for x in estimates)/len(estimates),2) if estimates else None
    total_model=round(sum(abs(x["projected_total"]-x["actual_total"]) for x in paired)/len(paired),2) if paired else None
    total_base=round(sum(abs(x["baseline_total"]-x["actual_total"]) for x in paired)/len(paired),2) if paired else None
    out={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "regular_season_games":len(regular),"chronological_scoring_tests":len(estimates),
         "margin_mean_absolute_error_points":mae("projected_margin","actual_margin"),
         "total_mean_absolute_error_points":mae("projected_total","actual_total"),
         "margin_zero_baseline_mae":margin_base,"paired_total_games":len(paired),"paired_model_total_mae":total_model,"paired_baseline_total_mae":total_base,
         "test_gate":"RESEARCH_ONLY",
         "limitations":"Prior five regular-season games per team. No injuries, opponent adjustment, rest, pace, market lines, fees, or verified Kalshi game matching. Errors describe score projections only, NOT profitable spread/total trades.",
         "examples":estimates[-12:]}
    (DOCS/"nba_scoring_audit.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    val=lambda x:"Not available" if x is None else str(x)
    block="<section style='background:#24344a;padding:18px;border-radius:12px;margin:18px 0'><h2>NBA spread and total research (Step 12H)</h2><p>Chronological regular-season score tests: "+str(len(estimates))+". Game margin average error: "+val(out["margin_mean_absolute_error_points"])+" points. Game total average error: "+val(out["total_mean_absolute_error_points"])+" points.</p><p style='color:#ffd184'>EXPERIMENTAL — these are score-estimation errors, not predicted betting edges. Kalshi contract settlement rules, market lines, executable prices and fees are not matched or verified.</p><p><a href='./nba_scoring_audit.json'>View scoring research audit</a></p></section>"
    block+="<section style='background:#24344a;padding:18px;border-radius:12px;margin:18px 0'><h2>NBA scoring benchmarks (Step 12I)</h2><p>Margin model MAE: "+val(out["margin_mean_absolute_error_points"])+"; neutral zero-margin baseline MAE: "+val(margin_base)+".</p><p>Totals matched on "+str(len(paired))+" games: model MAE "+val(total_model)+"; prior historical-average MAE "+val(total_base)+". Lower is better.</p><p style='color:#ffd184'>Research only. No matched Kalshi contract prices or realistic fills. Historical archive may be incomplete.</p></section>"
    p=DOCS/"index.html"
    if not p.exists():raise RuntimeError("Missing dashboard")
    p.write_text(p.read_text(encoding="utf-8").replace("</body></html>",block+"</body></html>"),encoding="utf-8")
    print("NBA scoring audit:",len(estimates),"chronological tests")
if __name__=="__main__":main()
