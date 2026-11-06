import map_symbols as m,json,sys,difflib,re
new=json.loads((m.OUT/'tfx.020-0.json').read_text());hs=m.load(m.GAME/'TFX.040')
def norm(t):return re.sub(r'\b[ad][0-7]\b','R',m.norm(t))
all=[]
for h in [0,5,6,12,14]:
 rs=json.loads((m.OUT/f'TFX.040-{h}.json').read_text());idx={x[0]:i for i,x in enumerate(rs)}
 for o,name in hs[h]['symbols']:
  if o in idx:all.append((h,o,name,[norm(x[2]) for x in rs[idx[o]:idx[o]+70]]))
for arg in sys.argv[1:]:
 o=int(arg,16);rs=list(m.records(str(m.OUT/'tfx.020-0.bin'),0,0,o,o+400,'68040'));ts=[norm(x[2]) for x in rs[:70]]
 scores=sorted([(difflib.SequenceMatcher(None,ts,txt,autojunk=False).ratio(),h,bo,name) for h,bo,name,txt in all],reverse=True)[:6]
 print(arg,[(round(s,3),h,hex(bo),name) for s,h,bo,name in scores])
