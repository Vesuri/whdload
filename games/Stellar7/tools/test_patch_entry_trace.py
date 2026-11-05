import unittest
from patch_entry_trace import observed_entries

class Entries(unittest.TestCase):
    def test_external_origin_cannot_hide_bad_target(self):
        with self.assertRaisesRegex(AssertionError,'patch-interior'):
            observed_entries([0x2000,0x1002],0x1000,{1,2,3,4,5},set())

    def test_gap_does_not_hide_bad_target(self):
        with self.assertRaises(AssertionError):
            observed_entries([None,0x7fffffff,0x1003],0x1000,{1,2,3},set())

    def test_declared_padding_and_entries(self):
        r=observed_entries([0x2000,0x1000,0x1004,None],0x1000,{1,2,3,4,5},{4})
        self.assertEqual(r['observed_instruction_pcs'],3)
        self.assertEqual(r['missing_pc_records'],1)
        self.assertEqual(r['declared_padding'],{'0x4':1})

    def test_empty_trace_rejected(self):
        with self.assertRaises(AssertionError):observed_entries([None],0,set(),set())

if __name__=='__main__':unittest.main()
