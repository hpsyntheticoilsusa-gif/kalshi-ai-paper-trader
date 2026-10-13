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
    # Human-readable mobile view of the same snapshot. Keep raw JSON for audits.
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kalshi Market Decisions</title><style>
    body{font:16px system-ui,Arial;background:#101827;color:#eff5ff;margin:0}main{max-width:730px;margin:auto;padding:20px 16px 45px}
    a{color:#9cc9ff}.panel{background:#22344b;border-radius:15px;padding:18px;margin:15px 0}.card{background:#17283e;border-radius:12px;margin:10px 0;padding:14px;overflow-wrap:anywhere}
    input,select{font:16px system-ui;width:100%;box-sizing:border-box;padding:13px;border:1px solid #67809c;border-radius:9px;background:#112136;color:white;margin:8px 0}
    small{color:#b9c6d6}strong{display:block;margin:4px 0}.tag{color:#ffdb8d;font-weight:800}button{padding:12px 20px;border:0;border-radius:10px;background:#37d67a;color:#081c12;font-weight:bold}
    </style></head><body><main><a href="./">← Dashboard</a><h1>Market research decisions</h1>
    <div class="panel"><p id="overview">Loading current scan…</p><p>Research only. PASS means no validated trading recommendation—not that YES or NO must lose.</p>
    <label for="query">Search market name or ticker</label><input id="query" type="search" placeholder="Search markets…">
    <label for="signal">Research direction</label><select id="signal"><option value="ALL">All directions</option><option>YES</option><option>NO</option><option>PASS</option></select>
    <p id="count" role="status"></p><div id="results"></div><button id="more" type="button" hidden>Show more</button></div>
    <p><a href="./research_directions.json">Raw JSON data</a></p></main><script>
    const $=id=>document.getElementById(id);let entries=[],limit=25;
    function draw(){const q=$('query').value.toLowerCase().trim(),side=$('signal').value;
      const filtered=entries.filter(x=>(side==='ALL'||x.signal===side)&&(!q||(String(x.title)+' '+String(x.ticker)).toLowerCase().includes(q)));
      $('count').textContent='Showing '+Math.min(limit,filtered.length)+' of '+filtered.length+' matching markets.';
      $('results').replaceChildren();
      for(const item of filtered.slice(0,limit)){const card=document.createElement('article');card.className='card';
       const title=document.createElement('strong');title.textContent=item.title||item.ticker;
       const ticket=document.createElement('small');ticket.textContent=item.ticker;
       const label=document.createElement('p');label.className='tag';label.textContent='Direction: '+item.signal;
       const why=document.createElement('p');why.textContent=item.reason;
       card.append(title,ticket,label,why);$('results').append(card);}
      $('more').hidden=filtered.length<=limit;
    }
    for(const id of ['query','signal'])$(id).addEventListener('input',()=>{limit=25;draw();});
    $('more').addEventListener('click',()=>{limit+=25;draw();});
    fetch('./research_directions.json?refresh='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()})
      .then(d=>{entries=Array.isArray(d.entries)?d.entries:[];$('overview').textContent='Scan: '+d.generated_utc+' · Markets reviewed: '+d.saved_markets_reviewed+' · YES '+d.yes+' · NO '+d.no+' · PASS '+d.pass;draw();})
      .catch(e=>{$('overview').textContent='Could not load current decisions: '+e.message;});
    </script></body></html>"""
    (DOCS/"market-decisions.html").write_text(page,encoding="utf-8")
    section="<section style='margin:20px 0;background:#24344a;border-radius:14px;padding:18px'><h2>YES / NO / PASS research indicator (Step 14)</h2><p>Filtered markets reviewed: "+str(len(rows))+". YES: 0 · NO: 0 · PASS: "+str(len(rows))+".</p><p style='color:#ffd184'><strong>PASS — no actionable prediction.</strong> A market will not receive a YES or NO direction without independently validated model probabilities, verified contract rules, real executable prices, fees and liquidity. This is a safety gate, not a trading recommendation.</p><p><a href='./market-decisions.html'>View market research decisions</a></p></section>"
    dash=DOCS/"index.html";raw=dash.read_text(encoding="utf-8")
    if "</body></html>" not in raw:raise RuntimeError("Dashboard closing tags missing")
    dash.write_text(raw.replace("</body></html>",section+"</body></html>"),encoding="utf-8")
    print("Direction gate: PASS",len(rows),"YES 0 NO 0")
if __name__=="__main__":main()
