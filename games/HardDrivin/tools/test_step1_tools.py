"""Failure-path tests for tools that guard later optimization comparisons."""
import copy,json,struct,tempfile,unittest
from pathlib import Path
from compare_state import differences,compare
from check_disabled import check
from capture_demo import ROOT
class ComparisonTests(unittest.TestCase):
 def setUp(self):
  self.a={'layout':{'regions':[dict(name='code',base=0x10000,size=0x1000),dict(name='data',base=0x20000,size=0x1000)]}}
  self.b=copy.deepcopy(self.a)
  for r in self.b['layout']['regions']:r['base']+=0x100000
 def test_relocation(self):
  x=struct.pack('>III',0x10102,0x20802,42);y=struct.pack('>III',0x110102,0x120802,42)
  self.assertTrue(differences(x,y,self.a,self.b));self.assertEqual(differences(x,y,self.a,self.b,True),[])
  z=y[:-1]+b'\x2b';self.assertEqual(differences(x,z,self.a,self.b,True),[11])
 def test_wrong_target(self):
  self.assertTrue(differences(struct.pack('>I',0x10102),struct.pack('>I',0x120102),self.a,self.b,True))
 def test_short(self):
  with self.assertRaises(ValueError):differences(b'abc',b'ab',self.a,self.b)
 def test_sets_and_lengths(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
   a,b=Path(temp)/'a',Path(temp)/'b'
   for d in [a,b]:
    (d/'vbl').mkdir(parents=True);(d/'metadata.json').write_text(json.dumps(dict(self.a,snapshot_regions=[dict(name='data',size=4)],snapshot_size=4)));(d/'vbl/000000.bin').write_bytes(b'abcd')
   self.assertEqual(compare(a,b,'vbl')['equal'],1)
   (b/'vbl/000000.bin').write_bytes(b'abc')
   with self.assertRaises(AssertionError):compare(a,b,'vbl')
   (b/'vbl/000000.bin').unlink()
   with self.assertRaises(AssertionError):compare(a,b,'vbl')
class DisabledTests(unittest.TestCase):
 def test_active_rejected_and_known_gate_skipped(self):
  d=ROOT/'tmp/prof/matrix-a500-smoke'
  self.assertFalse(check(d)['passed']);self.assertTrue(check(d,['VERIFY_ATTRACT'])['passed'])
 def test_mutation(self):
  src=ROOT/'tmp/prof/matrix-a500-smoke'
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
   d=Path(temp);(d/'metadata.json').write_bytes((src/'metadata.json').read_bytes());b=bytearray((src/'game-code.bin').read_bytes());b[0x756]^=1;(d/'game-code.bin').write_bytes(b)
   self.assertFalse(check(d,['VERIFY_ATTRACT'])['passed'])
if __name__=='__main__':unittest.main()
