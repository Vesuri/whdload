import map_symbols as m,json,struct,collections
hs=m.load(m.GAME/'TFX.040'); ns=m.load(m.GAME/'tfx.020'); spans=json.loads((m.OUT/'exact-symbol-spans.json').read_text()); votes=collections.defaultdict(collections.Counter)
for s in spans:
 h=hs[s['beta_hunk']]; start=s['beta_offset']; end=start+s['size'];delta=s['target']-start
 for tgt,offs in h['relocs'].items():
  for o in offs:
   if start<=o<end:
    no=o+delta
    nt=next((t for t,os in ns[0]['relocs'].items() if no in os),None)
    if nt is None:continue
    a=struct.unpack_from('>I',h['data'],o)[0];b=struct.unpack_from('>I',ns[0]['data'],no)[0]
    votes[tgt][(nt,b-a)]+=1
for i,h in enumerate(hs):
 print('\nHUNK',i,hex(len(h['data'])),votes[i].most_common(8))
 if i in [2,4,7,8,9,10]:
  print(h['symbols'])
