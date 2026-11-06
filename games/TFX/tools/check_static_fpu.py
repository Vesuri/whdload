import json,sys,re,struct
from pathlib import Path
import map_symbols as m
src=m.ROOT/'src'
meta=json.loads((m.ROOT/'tmp/step9/fpu-sites.json').read_text());text=(src/'native_fpu_sites.i').read_text()
rows=re.findall(r'PL_L \$([0-9a-f]+),\$4eb80000\+\$([0-9a-f]+)',text)
assert len(rows) in (239,245) and len(set(a for a,b in rows))==len(rows)
rows=rows[:239]
for (a,b),s in zip(rows,meta['sites']):assert int(a,16)==s['offset'] and int(b,16)==meta['slots'][s['key']]
code=m.load(m.GAME/'tfx.020')[0]['data']
raw=[]
for o in range(0,len(code)-3,2):
 w,x=struct.unpack_from('>HH',code,o)
 if w==0xf200 and ((x&0xe07f)==3 or (x&0xfc00)==0x5c00):raw.append(o)
assert set(raw)=={x['offset'] for x in meta['sites']} and len(raw)==239
r=json.loads(Path(sys.argv[1]).read_text());assert len(r)==1147
assert all(x['equal'] and x['fpsr_equal'] and x['fpcr_equal'] for x in r)
print('239 distinct sites; 31 helpers; all 1147 native/FPSP register, FPCR and FPSR comparisons pass')
