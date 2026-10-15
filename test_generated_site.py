"""Automated smoke checks for generated Kalshi Scanner static reports.
Run after the scan finishes; failures block publication to GitHub Pages.
"""
import json,pathlib,re,unittest
ROOT=pathlib.Path(__file__).parent
DOCS=ROOT/"docs"
class GeneratedSiteTests(unittest.TestCase):
    def read_json(self,name):
        path=DOCS/name
        self.assertTrue(path.is_file(),f"Missing {name}")
        return json.loads(path.read_text(encoding="utf-8"))
    def test_dashboard_and_mobile_pages(self):
        for name in ("index.html","paper-ticket.html","market-decisions.html"):
            p=DOCS/name
            self.assertTrue(p.is_file(),f"Missing {name}")
            txt=p.read_text(encoding="utf-8")
            self.assertIn("</html>",txt.lower())
            self.assertIn("</body>",txt.lower())
        decisions=(DOCS/"market-decisions.html").read_text(encoding="utf-8")
        self.assertIn("research_directions.json",decisions)
        self.assertIn("Search market name or ticker",decisions)
        self.assertIn("Direction:",decisions)
        self.assertIn("./market-decisions.html",(DOCS/"index.html").read_text(encoding="utf-8"))
    def test_decision_counts(self):
        report=self.read_json("research_directions.json")
        entries=report["entries"]
        self.assertIsInstance(entries,list)
        self.assertEqual(len(entries),report["research_entries"])
        self.assertEqual(len(entries),report["yes"]+report["no"]+report["pass"])
        self.assertTrue(all(e.get("signal") in ("YES","NO","PASS") for e in entries))
        self.assertTrue(all(e.get("ticker") and e.get("reason") for e in entries))
        self.assertEqual(report["yes"],0)
        self.assertEqual(report["no"],0)
        self.assertEqual(report["pass"],len(entries))
        for e in entries:
            if e.get("rough_yes_probability") is not None:
                p=float(e["rough_yes_probability"])
                self.assertTrue(0<=p<=1)
                self.assertAlmostEqual(p+float(e["rough_no_probability"]),1,places=3)
                self.assertIsNotNone(e.get("yes_ask_cents"))
                self.assertIsNotNone(e.get("no_ask_cents"))
    def test_settlement_feed(self):
        data=self.read_json("settlements.json")
        self.assertIsInstance(data.get("settlements"),list)
        for item in data["settlements"]:
            self.assertIsInstance(item.get("ticker"),str)
            if item.get("market_status")=="finalized":
                self.assertIn(item.get("result"),("yes","no"))
    def test_pwa(self):
        manifest=self.read_json("manifest.webmanifest")
        self.assertIn(manifest.get("display"),("standalone","fullscreen","minimal-ui"))
        self.assertTrue((DOCS/"sw.js").exists())
        for name in ("icon-192.png","icon-512.png"):
            self.assertTrue((DOCS/name).is_file(),f"Missing PWA icon {name}")
if __name__=="__main__":unittest.main()
