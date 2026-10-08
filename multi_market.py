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
    (DOCS/"market_categories.json").write_text(json.dumps({"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scope":"Only saved markets passing liquidity/spread filters; all qualifying saved from up to 20,000 scanned","categories":dict(grouped),"markets":out},indent=2),encoding="utf-8")
    # Publish full filtered dataset. The phone renders a limited page at a time.
    section='''<section id="all-markets" style="margin:20px 0;background:#1c2c42;padding:18px;border-radius:14px">
<h2>All-market explorer (Step 11)</h2><p>Search all saved qualifying markets from the latest scan. These are filtered snapshots, NOT every Kalshi market, live quotes, or validated trading signals. Categories use conservative ticker-prefix heuristics.</p>
<label for="marketSearch">Search market name or ticker</label>
<input id="marketSearch" type="search" placeholder="Search sports, weather, ticker…" style="display:block;width:100%;box-sizing:border-box;background:#122035;color:white;padding:13px;border:1px solid #66819b;border-radius:9px;font-size:16px;margin:8px 0 12px">
<label for="marketSort">Sort results</label><select id="marketSort" style="display:block;width:100%;background:#122035;color:white;padding:12px;border:1px solid #66819b;border-radius:9px;font-size:16px;margin:8px 0 12px"><option value="volume">Highest 24h volume</option><option value="spread">Tightest YES spread</option><option value="closing">Earliest closing</option></select>
<div id="catfilters" style="display:flex;flex-wrap:wrap;gap:8px;margin:14px 0"></div>
<p id="categoryCount" style="font-size:13px" role="status">Loading saved filtered markets…</p><div class="cards" id="categoryCards"></div>
<button id="moreMarkets" type="button" style="display:none;margin:16px auto;padding:13px;border-radius:10px;background:#37d67a;color:#07190d;font-weight:700;border:0">Show more markets</button>
<p><a href="./market_categories.json">Download complete filtered dataset (JSON)</a></p>
</section><style>.catbutton{padding:10px 12px;border-radius:10px;border:1px solid #53677c;background:#2d445e;color:#f1f5fd;font-size:14px;cursor:pointer}.catbutton[aria-pressed="true"]{background:#35d576;color:#091b13;font-weight:700}</style>
<script>(function(){
const cats=['All','Sports','Weather','Economics','Politics','Finance','Technology','Science','Other'];
const filters=document.getElementById('catfilters'),listing=document.getElementById('categoryCards'),counter=document.getElementById('categoryCount'),search=document.getElementById('marketSearch'),sort=document.getElementById('marketSort'),more=document.getElementById('moreMarkets');
let all=[],selected='All',limit=30;
function node(tag,klass,content){const el=document.createElement(tag);if(klass)el.className=klass;if(content!==undefined)el.textContent=content;return el;}
function redraw(){
const q=search.value.trim().toLowerCase();
const matches=all.filter(m=>(selected==='All'||m.category===selected)&&(!q||(String(m.title)+' '+String(m.ticker)+' '+String(m.category)).toLowerCase().includes(q)));
const num=m=>Number(m)||0;
matches.sort((a,b)=>sort.value==='spread'?num(a.spread_cents)-num(b.spread_cents)||num(b.volume_24h)-num(a.volume_24h):sort.value==='closing'?String(a.close_time||'9999').localeCompare(String(b.close_time||'9999')):num(b.volume_24h)-num(a.volume_24h));
listing.replaceChildren();
for(const m of matches.slice(0,limit)){
const card=node('article','market'),tag=node('div','tag',m.category),name=node('strong','',m.title),ticker=node('p','ticker',m.ticker),prices=node('div','prices');
for(const [label,value] of [['YES ask',m.yes_ask_cents+'¢'],['NO ask',m.no_ask_cents+'¢'],['YES spread',m.spread_cents+'¢'],['24h vol',num(m.volume_24h).toLocaleString()]]){const span=node('span','',label),b=node('b','',value);span.append(b);prices.append(span);}
card.append(tag,name,ticker,prices);listing.append(card);
}
counter.textContent='Showing '+Math.min(limit,matches.length)+' of '+matches.length+' matching markets; '+all.length+' qualifying markets saved.';
more.style.display=matches.length>limit?'block':'none';
for(const btn of filters.querySelectorAll('button'))btn.setAttribute('aria-pressed',String(btn.dataset.category===selected));
}
function filterButtons(){
filters.replaceChildren();
for(const cat of cats){const count=cat==='All'?all.length:all.filter(x=>x.category===cat).length;const btn=node('button','catbutton',cat+' ('+count+')');btn.type='button';btn.dataset.category=cat;btn.addEventListener('click',()=>{selected=cat;limit=30;redraw();});filters.append(btn);}
}
search.addEventListener('input',()=>{limit=30;redraw();});sort.addEventListener('change',()=>{limit=30;redraw();});more.addEventListener('click',()=>{limit+=30;redraw();});
fetch('./market_categories.json?refresh='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Data unavailable');return r.json();}).then(data=>{if(!Array.isArray(data.markets))throw Error('Bad market data');all=data.markets;filterButtons();redraw();}).catch(()=>{counter.textContent='Category data unavailable. Try refreshing after the next GitHub scan.';});
})();</script>'''
    p=DOCS/"index.html"
    if not p.exists():raise RuntimeError("Scanner dashboard missing")
    current=p.read_text(encoding="utf-8")
    p.write_text(current.replace("</body></html>",section+"</body></html>"),encoding="utf-8")
    print("Category explorer:",len(out),"markets,counts",dict(grouped))
if __name__=="__main__":main()
