from pathlib import Path
import sys,json,re,gzip,tempfile,shutil,collections,os
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'/sys.argv[1]
j=json.loads((p/'result.json').read_text());probe=int(j['probe'],16)
listing=(Path(j['slave']).parent/'fine.list').read_text();syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)}
short_entry=probe+int(re.search(r'^00:([0-9A-F]{8})',listing.split('.short:',1)[1],re.M)[1],16);short_count=0
start=probe+syms['FF1Divide000'];ends={probe+syms['FF1DivDone']+4}
if 'FF1C4DividePositive' in syms:
 from capstone import Cs,CS_ARCH_M68K,CS_MODE_BIG_ENDIAN,CS_MODE_M68K_000
 code=(Path(j['slave']).parent/'fine.bin').read_bytes();lo=syms['FF1C4DividePositive'];hi=syms.get('FF1DivFastEnd',syms.get('FF1DivFastControl'))
 for ins in Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000).disasm(code[lo:hi],lo):
  if ins.mnemonic=='rts':ends.add(probe+ins.address)
file=p/'detail.bin';temp=None
if not file.exists():
 fd,path=tempfile.mkstemp(prefix='ff1-divhist-',suffix='.bin',dir=r/'tmp');os.close(fd);temp=Path(path)
 with gzip.open(p/'detail.bin.gz','rb') as a,temp.open('wb') as b:shutil.copyfileobj(a,b)
 file=temp
try:
 t=barto.load(file);rows=collections.defaultdict(lambda:dict(calls=0,cycles=0,numerators=collections.Counter(),callers=collections.Counter()));cur=None;updates=0;previous_pc=None;native_caller=None
 for f in t.fields:
  for pc,cost,regs in t.instructions(f):
   if pc==short_entry:short_count+=1
   if pc==0x65174:updates+=1
   if pc==0x293d0:native_caller=previous_pc
   if pc==start:
    assert cur is None
    n,d=regs[0],regs[1];cur=[n,d,0,native_caller if previous_pc==0x293d0 else previous_pc]
   if cur is not None:
    cur[2]+=cost
    if pc in ends:
     n,d,c,caller=cur;row=rows[d];row['calls']+=1;row['cycles']+=c;row['numerators'][n]+=1;row['callers'][caller]+=1;cur=None
   previous_pc=pc
 out=dict(trace=p.name,scope='Complete helper calls in retained trace; includes IRQ/stall cost. Update-entry count is descriptive, not a matched cycle gate.',update_entries=updates,short_path_calls=short_count,divisors=[dict(divisor=hex(k),signed=k if k<0x80000000 else k-0x100000000,calls=v['calls'],cycles=v['cycles'],mean_cycles=v['cycles']/v['calls'],callers=[dict(pc=hex(a),count=b) for a,b in v['callers'].most_common()],numerators=[dict(value=hex(a),count=b) for a,b in v['numerators'].most_common(20)]) for k,v in sorted(rows.items(),key=lambda q:-q[1]['cycles'])])
 (p/'division-histogram.json').write_text(json.dumps(out,indent=2)+'\n')
 print('updates',updates,'short path calls',short_count)
 for v in out['divisors']:print(v['signed'],v['calls'],v['cycles'],round(v['mean_cycles'],1))
finally:
 if temp is not None:temp.unlink()
