import os,re,sys,json,struct
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 route(s);listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1');symbol=lambda n:int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16);base=rd(s,0x87480)-symbol('step_main')
 cases=json.loads(Path('tmp/f-sort-selftest-cases.json').read_text())
 for j,keys in enumerate(cases):
  expected=[]
  for i,k in enumerate(keys):
   at=0
   while at<len(expected) and not ((k-keys[expected[at]])&0x80000000):at+=1
   expected.insert(at,i)
  order=list(struct.unpack('>'+str(len(keys))+'H',read_bytes(s,base+symbol(f'f_test_ids{j}'),len(keys)*2)))
  assert order==expected,(j,keys,order,expected)
  actual=read_bytes(s,base+symbol(f'f_test_out{j}'),4*len(keys));assert actual==b''.join(struct.pack('>I',keys[i]) for i in expected)
  rows.append(dict(case=j,count=len(keys),order=order))
 (s.out/'cases.json').write_text(json.dumps(rows,indent=2));print('exact native stable order:',len(rows),'cases',flush=True)
finally:s.quit()
