from pathlib import Path
import json,struct,re
r=Path(__file__).resolve().parents[1];base=r/'tmp/build/production-matched';build=json.loads((base/'build.json').read_text());out=r/'tmp/build/production-frames';out.mkdir(exist_ok=True)
def sy(p):return {n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',p.read_text(errors='replace'),re.M)}
for kind,accepted in [('000','step5-c4-divide-frame-r3g-v1-ab/000/candidate.slave'),('020','step5-c2/020/candidate.slave'),('fine','step5-b8-v3-source/lean/fine.slave')]:
 for arm in ['production','accepted']:
  original=base/'FerrariFormulaOne.slave' if arm=='production' else r/'tmp/build'/accepted
  raw=original.read_bytes();code=bytearray(raw[32:-4]);header=bytearray(raw[:32]);code+=bytes(build['bytes']-len(raw)) if 'bytes' in build else b''
  if arm=='production':info=build['payloads'][kind];symbols=info['symbols'];offset=info['offset'];listing=(base/kind/'fine.list').read_text()
  else:symbols=sy(original.parent/'fine.list');offset=len((r/'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave').read_bytes())-36;listing=(original.parent/'fine.list').read_text()
  if arm=='accepted':
   target=(base/'FerrariFormulaOne.slave').stat().st_size-36
   code+=bytes(target-len(code))
  if kind!='fine':
   matches=list(re.finditer(r'^00:([0-9A-F]{8}) 66[0-9A-F]{2}\s+\d+:\s+bne.b .behind',listing,re.M));assert len(matches)==1
   at=offset+int(matches[0][1],16);assert code[at]==0x66;code[at:at+2]=bytes.fromhex('4e71')
  else:
   begin=symbols['FF1PresentationAfterTick'];end=symbols['B8DrawEnabled'];chunk=code[offset+begin:offset+end]
   # Only the due branch is changed; the draw-enable switch remains true.
   rows=[(int(m[1],16),m[2]) for m in re.finditer(r'^00:([0-9A-F]{8}) (66[0-9A-F]{2})\s+\d+:\s+bne.b .done',listing,re.M) if begin<=int(m[1],16)<end];assert len(rows)==1,rows
   at=offset+rows[0][0];code[at:at+2]=bytes.fromhex('4e71')
   # Render the same endpoint pose in both arms, independent of wall-time alpha.
   start=symbols['B8PrepareRenderCopies'];end=symbols['B8PublishProjection'];lines=listing.splitlines();anchor=None;late=None
   for line in lines:
    m=re.match(r'^00:([0-9A-F]{8})\s+[0-9A-F]+\s+\d+:\s+(.*)',line)
    if not m:continue
    pc=int(m[1],16)
    if not start<=pc<end:continue
    if 'lea (schedule_context.l,pc),a0' in m[2]:anchor=pc
    if m[2].strip()=='moveq #100,d6':late=pc
   assert anchor is not None and late is not None
   code[offset+anchor:offset+anchor+4]=bytes.fromhex('6000')+struct.pack('>h',late-anchor-2)
  struct.pack_into('>I',header,20,len(code)//4);struct.pack_into('>I',header,28,len(code)//4)
  target=out/f'{arm}-{kind}.slave';target.write_bytes(header+code+bytes.fromhex('000003f2'))
  (out/f'{arm}-{kind}.json').write_text(json.dumps({'symbols':symbols,'offset':offset,'host_symbols':build['host_symbols'] if arm=='production' else sy(r/'tmp/build/step5-b7-loader-v3/build.list'),'listing':str(base/kind/'fine.list' if arm=='production' else original.parent/'fine.list')}))
print('Built equal-sized, every-update frame fixtures; fine alpha=100 in both arms')
