import map_symbols as m
import json,bisect,csv,re
p=m.OUT;maps=json.loads((p/'block-maps.json').read_text());syms=json.loads((p/'candidate-symbols.json').read_text());beta=m.load(m.GAME/'TFX.040')
rev={}
for key,mp in maps.items():
 if key.startswith('beta'):
  h=int(key.split('-')[1]);names=sorted(beta[h]['symbols']);offs=[x[0] for x in names]
  for old,v in mp.items():
   o=int(old);i=bisect.bisect_right(offs,o)-1
   if i>=0:rev[v['target']]=(h,o,names[i],v['block'])
for r in csv.DictReader((m.ROOT/'tmp/step5/strict1/routine-costs.csv').open()):
 if float(r['percent'])<.5:continue
 print(r['start'],r['name'],rev.get(int(r['start'],16)) if r['start'].startswith('0x') else 'external')
src=(m.ROOT/'src/TFXHD.s').read_text();part=src.split('\npl_020\n')[1].split('PL_END\n')[0]
for line in part.splitlines():
 if line.lstrip().startswith(';'):continue
 x=re.search(r'PL_(\w+)\s+\$([0-9a-fA-F]+),(.+)',line)
 if not x:continue
 op,off,tail=x.groups();o=int(off,16);v=maps['plain-0'].get(str(o));print('PATCH',op,off,tail.strip(),'->',hex(v['target']) if v else None,rev.get(v['target']) if v else '')
