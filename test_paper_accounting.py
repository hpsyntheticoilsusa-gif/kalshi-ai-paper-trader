"""Pure accounting invariants for browser paper-trading semantics."""
import unittest

START=100000
def cost(price,qty,fee):return round(price*qty+fee)
def payout(side,result,qty):
    return 100*qty if result in ("yes","no") and side==result else 0
def cash(trades):
    return START-sum(cost(t["price"],t["qty"],t["fee"])-payout(t["side"],t.get("result"),t["qty"]) for t in trades)
def settle_once(t,result):
    if t.get("result") in ("yes","no"):return t
    if result not in ("yes","no"):return t
    return {**t,"result":result}
class PaperAccountingTests(unittest.TestCase):
    def test_losing_position(self):
        trade=dict(price=55,qty=1,fee=2,side="yes")
        self.assertEqual(cash([trade]),99943)
        settled=settle_once(trade,"no")
        self.assertEqual(cash([settled]),99943)
        self.assertEqual(payout("yes","no",1),0)
    def test_winning_position_and_double_settlement(self):
        trade=dict(price=55,qty=1,fee=2,side="yes")
        win=settle_once(trade,"yes")
        self.assertEqual(cash([win]),100043)
        self.assertEqual(settle_once(win,"yes"),win)
        self.assertEqual(settle_once(win,"no"),win)
    def test_unknown_or_open_never_paid(self):
        trade=dict(price=20,qty=2,fee=3,side="no")
        self.assertEqual(settle_once(trade,None),trade)
        self.assertEqual(cash([trade]),99957)
    def test_mixed_positions(self):
        a=settle_once(dict(price=55,qty=1,fee=2,side="yes"),"no")
        b=settle_once(dict(price=30,qty=2,fee=3,side="no"),"no")
        self.assertEqual(cash([a,b]),100080)
if __name__=="__main__":unittest.main()
