"""Contract discovery gates should never promote price data to NFL picks."""
import datetime as dt
import unittest
from nfl_research import classify, inspect

class NFLResearchTests(unittest.TestCase):
    def test_non_nfl_is_excluded(self):
        self.assertIsNone(classify("KXNBAGAME-26NOV08-A"))
    def test_props_are_not_winner_trades(self):
        self.assertEqual(classify("KXNFLTD-26NOV08DENCAR-DENBNIX10-2"), "TOUCHDOWN_PROP")
        self.assertEqual(classify("KXNFLOT-26NOV08DENCAR-Y"), "OVERTIME")
        self.assertEqual(classify("KXNFL1HSPREAD-26NOV08DENCAR-X"), "PARTIAL_GAME")
    def test_unknown_nfl_is_not_assumed_winner(self):
        self.assertEqual(classify("KXNFLWEIRD-XYZ"), "OTHER_NFL_CONTRACT")
    def test_all_observations_pass_with_no_paper_trade(self):
        future=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=1)).isoformat()
        rows=[{"ticker":"KXNFLGAME-TEST","title":"A vs B","close_time":future,"yes_ask_cents":"48","no_ask_cents":"53"},
              {"ticker":"KXNBAGAME-TEST","title":"C vs D","close_time":future}]
        found=inspect(rows)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0]["future_close"])
        self.assertEqual(found[0]["signal"], "PASS")
        self.assertIsNone(found[0]["independent_probability"])
        self.assertIsNone(found[0]["validated_net_edge"])
        self.assertEqual(found[0]["paper_quantity"], 0)
    def test_bad_date_is_not_future(self):
        self.assertFalse(inspect([{"ticker":"KXNFLOT-TEST","close_time":"bad"}])[0]["future_close"])

if __name__=="__main__":
    unittest.main()
