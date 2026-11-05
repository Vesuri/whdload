import copy
import unittest
from power_route_state import validate_rows

class PowerRoute(unittest.TestCase):
    def rows(self):
        initial=dict(tick=0,inventory='03010101010101',selected=65535,timers=[0]*7,height=0,level=0)
        rows=[initial]
        for i,slot in enumerate((0,1,2,4,5,6)):
            r=copy.deepcopy(rows[-1]);r['tick']=i+1;r['selected']=slot;r['timers'][slot]=100
            inv=bytearray.fromhex(r['inventory']);inv[slot]=254 if slot==0 else 0;r['inventory']=inv.hex()
            if slot==2:r['height']=20
            rows.append(r)
        r=copy.deepcopy(rows[-1]);r.update(tick=20,height=0);r['timers'][2]=0;rows.append(r)
        return rows

    def test_complete(self):validate_rows(self.rows())

    def test_reject_mine_or_missing_charge(self):
        for field,value in [('inventory','fe000000000000'),('inventory','fe000001000001')]:
            r=self.rows();r[-1][field]=value
            with self.assertRaises(AssertionError):validate_rows(r)

    def test_reject_missing_jump_or_overlap(self):
        r=self.rows()
        for row in r:row['height']=0
        with self.assertRaises(AssertionError):validate_rows(r)
        r=self.rows();r[-2]['timers'][2]=0
        with self.assertRaises(AssertionError):validate_rows(r)

    def test_reject_reordered_activations(self):
        r=self.rows();r[1]['timers'][1]=100
        with self.assertRaises(AssertionError):validate_rows(r)

if __name__=='__main__':unittest.main()
