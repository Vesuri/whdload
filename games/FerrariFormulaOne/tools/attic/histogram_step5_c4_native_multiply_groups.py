from pathlib import Path
import sys,json,re,gzip,tempfile,shutil,collections,os
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
from capstone import Cs,CS_ARCH_M68K,CS_MODE_BIG_ENDIAN,CS_MODE_M68K_000
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'/sys.argv[1];j=json.loads((p/'result.json').read_text());probe=int(j['probe'],16);b=Path(j['slave']).parent
syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',(b/'fine.list').read_text(),re.M)}
lo=syms['FF1MultiplyNative200'];hi=syms['FF1MultiplyNative200Signature'];code=(b/'fine.bin').read_bytes();start=probe+lo
ends={probe+i.address for i in Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000).disasm(code[lo:hi],lo) if i.mnemonic=='rts'}
fd,name=tempfile.mkstemp(dir=r/'tmp',prefix='ff1-mulhist-',suffix='.bin');os.close(fd);temp=Path(name)
try:
 with gzip.open(p/'detail.bin.gz','rb') as a,temp.open('wb') as c:shutil.copyfileobj(a,c)
 t=barto.load(temp);rows=collections.defaultdict(lambda:dict(calls=0,cycles=0,positive_words=0,signed_words=0,pairs=collections.Counter()));cur=None;prev=None;caller=None;groups=collections.defaultdict(lambda:dict(calls=0,cycles=0))
 for f in t.fields:
  for pc,cost,regs in t.instructions(f):
   if pc==0x29500:caller=prev
   if pc==start:
    assert cur is None
    cur=[caller if prev==0x29500 else prev,regs[0],regs[1],0]
   if cur is not None:
    cur[3]+=cost
    if pc in ends:
     at,a,b,c=cur
     signedword=lambda v:v<32768 or v>=0xffff8000
     key='zero' if a==0 or b==0 else 'both_unsigned_words' if a<65536 and b<65536 else 'both_signed_words' if signedword(a) and signedword(b) else 'positive_word_long' if a<0x80000000 and b<0x80000000 and min(a,b)<65536 else 'other'
     groups[key]['calls']+=1;groups[key]['cycles']+=c
     row=rows[at];row['calls']+=1;row['cycles']+=c;row['positive_words']+=a<65536 and b<65536;row['signed_words']+=all(x<32768 or x>=0xffff8000 for x in (a,b));row['pairs'][(a,b)]+=1;cur=None
   prev=pc
 out=dict(operand_groups=dict(groups),trace=p.name,scope='Complete native multiply calls, including IRQ/stall cost; caller histogram for planning only.',callers=[dict(pc=hex(at),calls=v['calls'],cycles=v['cycles'],mean_cycles=v['cycles']/v['calls'],positive_words=v['positive_words'],signed_words=v['signed_words'],pairs=[dict(a=hex(a),b=hex(b),count=n) for (a,b),n in v['pairs'].most_common(20)]) for at,v in sorted(rows.items(),key=lambda x:-x[1]['cycles'])])
 (p/'native-multiply-groups.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps(out['operand_groups'],indent=2))
 for v in out['callers'][:5]:print(v['pc'],v['calls'],v['cycles'],round(v['mean_cycles'],1),v['positive_words'],v['signed_words'])
finally:temp.unlink()
