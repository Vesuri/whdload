import sys,json,re,random,struct,os
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 route(s)
 listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1');symbol=lambda n:int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
 base=rd(s,0x87480)-symbol('step_main');entry=base+symbol('f_sort');scratch=base+symbol('f_text_cache');stop=base+symbol('f_glyph_native')
 s.cmd(f'break *{stop:#x}');s.cmd('set $sr=0x2700')
 rng=random.Random(1234)
 cases=[[9]*12,list(range(62,-1,-1)),list(range(63)),[3,1,3,1,2,2],[],[1],[0x7fff0000,0x80000000,0,0xffff0000],[0xffff0000,0,0x7fff0000,0x80000000]]
 cases += [[rng.randrange(0,8)*65536+rng.randrange(3) for i in range(n)] for n in [4,32,32,2,63,64,5,5]]
 def before(x,y):return bool((x-y)&0x80000000)
 for j,keys in enumerate(cases):
  # Native always copies the first word, even for an empty list. Test empty only for safe return.
  expected=[]
  for i,k in enumerate(keys):
   at=0
   while at<len(expected) and not before(k,keys[expected[at]]):at+=1
   expected.insert(at,i)
  blob=struct.pack('>'+str(len(keys)+1)+'I',*keys,0xffffffff)
  for off in range(0,len(blob),4):
   value=struct.unpack_from('>I',blob,off)[0]
   print(s.cmd(f'set {{unsigned int}}{scratch+off:#x}={value:#x}'),flush=True)
  actual=read_bytes(s,scratch,len(blob));assert actual==blob,(actual.hex(),blob.hex())
  for reg,value in [('a0',scratch),('a1',scratch+512),('a2',scratch+1024),('sp',scratch+2044),('pc',entry)]:print(reg,s.cmd(f'set ${reg}={value:#x}'),flush=True)
  s.cmd(f'set {{unsigned int}}{scratch+2044:#x}={stop:#x}');print(s.cmd('info registers'),flush=True);print(s.cmd('continue',timeout=60),flush=True);print(s.cmd('info registers'),flush=True)
  order=list(struct.unpack('>'+str(len(keys))+'H',read_bytes(s,scratch+1024,len(keys)*2))) if keys else []
  assert order==expected,(j,keys,order,expected)
  actual=read_bytes(s,scratch+512,4*len(keys));assert actual==b''.join(struct.pack('>I',keys[i]) for i in expected)
  rows.append(dict(case=j,count=len(keys),order=order))
 (s.out/'cases.json').write_text(json.dumps(rows,indent=2));print('exact native stable order:',len(rows),'cases',flush=True)
finally:s.quit()
