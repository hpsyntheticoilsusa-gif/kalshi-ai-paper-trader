"""Category overview of already-screened public Kalshi markets; no predictions or orders."""
import csv, json, pathlib, html, datetime, collections
ROOT=pathlib.Path(__file__).parent; DATA=ROOT/"data"; DOCS=ROOT/"docs"
CATEGORIES=("Sports","Weather","Economics","Politics","Finance","Technology","Science","Other")
def category(ticker,title):
    t=(ticker or "").upper(); name=(title or "").lower()
    # Conservative series-prefix heuristics. Uncertain markets stay in Other.
    sport=("NFL","NBA","MLB","NHL","NCA","ATP","WTA","ITF","UFC","PGA","FIFA","SOCCER","TENNIS","MATCH","GAME","ESPORT","DOTA","CS2","F1","GOLF")
    if any(t.startswith("KX"+s) for s in sport):return "Sports"
    if any(t.startswith("KX"+s) for s in ("TEMP","HIGH","LOW","RAIN","SNOW","HURRICANE","WEATHER","TORNADO")):return "Weather"
    if any(t.startswith("KX"+s) for s in ("CPI","FED","FOMC","GDP","JOBS","UNEMPLOY","PCE","INFLATION","AAAGAS","GASPRICE")):return "Economics"
    if any(t.startswith("KX"+s) for s in ("ELECTION","PRES","SENATE","HOUSE","GOVERNOR","CONGRESS","POLITIC","TRUMP","BIDEN")):return "Politics"
    if any(t.startswith("KX"+s) for s in ("SPX","NASDAQ","DOW","BITCOIN","BTC","ETH","STOCK","CRYPTO")):return "Finance"
    if any(t.startswith("KX"+s) for s in ("AI","OPENAI","APPLE","TECH","PRODUCT")):return "Technology"
    if any(t.startswith("KX"+s) for s in ("QUAKE","BIGGESTQUAKE","SPACE","ROCKET","NASA")):return "Science"
    return "Other"
def main():
    with (DATA/"latest_markets.csv").open(newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
    grouped=collections.Counter()
    out=[]
    for r in rows:
        cat=category(r.get("ticker"),r.get("title"))
        grouped[cat]+=1
        out.append({**r,"category":cat})
    (DOCS/"market_categories.json").write_text(json.dumps({"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scope":"Only saved markets passing liquidity/spread filters; at most 500 from up to 4000 scanned","categories":dict(grouped),"markets":out},indent=2),encoding="utf-8")
    esc=lambda x:html.escape(str(x),quote=True)
    chips=''.join('<button type="button" class="catbutton" data-category="'+esc(cat)+'">'+esc(cat)+' ('+str(grouped[cat])+')</button>' for cat in CATEGORIES)
    cards=''.join('<article class="market catmarket" data-category="'+esc(x["category"])+'"><div class="tag">'+esc(x["category"])+'</div><strong>'+esc(x["title"])+'</strong><p class="ticker">'+esc(x["ticker"])+'</p><div class="prices"><span>YES ask <b>'+esc(x["yes_ask_cents"])+'¢</b></span><span>NO ask <b>'+esc(x["no_ask_cents"])+'¢</b></span><span>YES spread <b>'+esc(x["spread_cents"])+'¢</b></span><span>24h vol <b>'+esc(x["volume_24h"])+'</b></span></div></article>' for x in out[:150])
    section='''<section id="all-markets" style="margin:20px 0;background:#1c2c42;padding:18px;border-radius:14px"><h2>All-market explorer (Step 9)</h2><p>Markets below are grouped from the current <b>filtered</b> Kalshi scan (up to 500 saved from up to 4,000 fetched). Not a complete exchange catalog. Categories are rule-of-thumb labels, not verified Kalshi metadata. Prices are snapshots, not live quotes; no category-specific predictive advantage is claimed.</p><div id="catfilters" style="display:flex;flex-wrap:wrap;gap:8px;margin:14px 0"><button type="button" class="catbutton" data-category="All">All ('''+str(len(out))+''')</button>'''+chips+'''</div><p id="categoryCount" style="font-size:13px">Showing '''+str(min(len(out),150))+''' of '''+str(len(out))+''' filtered markets. Top 150 shown by scan ranking.</p><div class="cards" id="categoryCards">'''+cards+'''</div><p><a href="./market_categories.json">Download category data (JSON)</a></p></section><style>.catbutton{padding:10px 12px;border-radius:10px;border:1px solid #53677c;background:#2d445e;color:#f1f5fd;font-size:14px;cursor:pointer}.catbutton[aria-pressed="true"]{background:#35d576;color:#091b13;font-weight:700}</style><script>(function(){const buttons=[...document.querySelectorAll(".catbutton")],cards=[...document.querySelectorAll(".catmarket")],count=document.getElementById("categoryCount");function choose(v){let visible=0;for(const c of cards){const yes=v==="All"||c.dataset.category===v;c.hidden=!yes;if(yes)visible++;}for(const b of buttons)b.setAttribute("aria-pressed",String(b.dataset.category===v));count.textContent="Showing "+visible+" of "+'''+str(len(out))+'''+ " filtered markets (top 150 rendered)."+(v==="All"?"":" Category: "+v);}for(const b of buttons)b.addEventListener("click",()=>choose(b.dataset.category));choose("All");})();</script>'''
    p=DOCS/"index.html"
    if not p.exists():raise RuntimeError("Scanner dashboard missing")
    current=p.read_text(encoding="utf-8")
    p.write_text(current.replace("</body></html>",section+"</body></html>"),encoding="utf-8")
    print("Category explorer:",len(out),"markets,counts",dict(grouped))
if __name__=="__main__":main()
