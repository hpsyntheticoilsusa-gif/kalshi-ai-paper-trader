"""Conservative YES/NO/PASS research gate. No model is live-approved."""
import csv,json,pathlib,datetime,collections
ROOT=pathlib.Path(__file__).parent;DATA=ROOT/"data";DOCS=ROOT/"docs"
def direction(yes_ask,no_ask,yes_probability=None,validated=False,fee_cents=3,min_edge_cents=8):
    """A recommendation requires independently validated probability + both tradable quotes.
    Probability absent/unvalidated => PASS, never infer p from market price.
    """
    if not validated:return {"signal":"PASS","reason":"Probability model not independently validated"}
    if yes_probability is None or not (0<yes_probability<1):return {"signal":"PASS","reason":"No valid probability"}
    try:yes=float(yes_ask);no=float(no_ask)
    except (TypeError,ValueError):return {"signal":"PASS","reason":"Missing executable price"}
    if not (1<=yes<=99 and 1<=no<=99):return {"signal":"PASS","reason":"Invalid market quotes"}
    # Indicative asks cannot establish fillability. Even validated probabilities
    # remain gated until separately verified execution evidence is integrated.
    return {"signal":"PASS","reason":"Execution depth, fees and contract settlement still unverified"}
def main():
    with (DATA/"latest_markets.csv").open(newline="",encoding="utf-8") as f:markets=list(csv.DictReader(f))
    rows=[{"ticker":m["ticker"],"title":m.get("title",""),**direction(m.get("yes_ask_cents"),m.get("no_ask_cents"))} for m in markets]
    report={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "saved_markets_reviewed":len(rows),"yes":0,"no":0,"pass":len(rows),
      "policy":"ALL PASS until independently validated event-specific probabilities, contract settlement rules, orderbook liquidity, costs, and forward results are available.",
      "entries":rows}
    (DOCS/"research_directions.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    section="<section style='margin:20px 0;background:#24344a;border-radius:14px;padding:18px'><h2>YES / NO / PASS research indicator (Step 14)</h2><p>Filtered markets reviewed: "+str(len(rows))+". YES: 0 · NO: 0 · PASS: "+str(len(rows))+".</p><p style='color:#ffd184'><strong>PASS — no actionable prediction.</strong> A market will not receive a YES or NO direction without independently validated model probabilities, verified contract rules, real executable prices, fees and liquidity. This is a safety gate, not a trading recommendation.</p><p><a href='./research_directions.json'>View market research decisions</a></p></section>"
    dash=DOCS/"index.html";raw=dash.read_text(encoding="utf-8")
    if "</body></html>" not in raw:raise RuntimeError("Dashboard closing tags missing")
    dash.write_text(raw.replace("</body></html>",section+"</body></html>"),encoding="utf-8")
    print("Direction gate: PASS",len(rows),"YES 0 NO 0")
if __name__=="__main__":main()
