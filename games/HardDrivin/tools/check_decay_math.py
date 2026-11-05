import json,os,re,shutil,struct
from decimal import Decimal as D,getcontext
from capture_demo import ROOT
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof/s4-decay-wide';out.mkdir(exist_ok=False)
for ext in ['slave','lst']:shutil.copyfile(ROOT/'tmp/build'/('s4-decay-math.'+ext),out/('slave.'+ext))
s=Session(out,'a500',out/'slave.slave',0x8520)
try:
 s.boot();images=s.dump_banks('decay');symbols={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (_[A-Za-z][A-Za-z0-9_]*)(?:\s|$)',(out/'slave.lst').read_text(errors='replace'),re.M)};slave=s.layout['published']-symbols['_code_start']
 def read(addr,size):
  for base,b in images:
   if base<=addr and addr+size<=base+len(b):return b[addr-base:addr-base+size]
  raise AssertionError(hex(addr))
 getcontext().prec=60;bases=[D(7)/8,D(9)/10,D(3)/4];names=['throttle','spin','contact'];table_words=0
 for name,base in zip(names,bases):
  expected=[]
  for n in range(65536):
   v=int(((1-base**(D(n)/8))*65536).to_integral_value())
   if v==65536:break
   expected.append(v)
  got=struct.unpack('>'+str(len(expected))+'H',read(slave+symbols['_decay_'+name+'_table'],len(expected)*2));assert got==tuple(expected);table_words+=len(expected)
 fields=[0,1,7,8,9,15,16,31,32,63,64,127,128,255,256,327,328,706,707,894,895,32767,32768,65535]
 expected=[int(((1-base**(D(n)/8))*65536).to_integral_value()) for n in fields for base in bases]
 got=struct.unpack('>72I',read(slave+symbols['_decay_test_results'],288));assert got==tuple(expected),(got,expected)
 result=dict(passed=True,table_words=table_words,runtime_coefficients=len(got),fields=fields);(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
