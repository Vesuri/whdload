"""Reject missed, reordered and collateral changes in the native toggle sequence."""
import unittest
from preferences_state import validate_sequence

class Sequence(unittest.TestCase):
    def rows(self):
        rows=[[1,1,1,1]]
        for i in range(8):
            row=rows[-1].copy();row[i%4]^=1;rows.append(row)
        return rows

    def test_round_trip(self):
        validate_sequence(self.rows(),8)

    def test_reject_missing_restore(self):
        rows=self.rows();rows[-1][3]=0
        with self.assertRaises(AssertionError):validate_sequence(rows,8)

    def test_reject_collateral_change(self):
        rows=self.rows();rows[1][2]=0
        with self.assertRaises(AssertionError):validate_sequence(rows,8)

    def test_reject_wrong_order_and_incomplete(self):
        rows=self.rows();rows[1]=[1,0,1,1]
        with self.assertRaises(AssertionError):validate_sequence(rows,8)
        with self.assertRaises(AssertionError):validate_sequence(self.rows(),7)

if __name__=='__main__':unittest.main()
