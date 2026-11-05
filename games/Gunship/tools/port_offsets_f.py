from pathlib import Path
import re,json
src=Path('src')
# Explicitly native code-hunk values below the main flight loop.
low={
 'timing-cockpit.i':set(),
 'timing-display.i':{0xb7c,0x44b4,0x44b6,0xba2},
 'timing-live-input.i':{0xfa0,0xfa2,0xfc6,0xfca,0x1068,0x34c8,0x34cc,0x4dc6,0x4dc8,0xc8c,0x4e2a},
 'timing-live-vbl.i':{0x4baa,0x4bbc,0x4c34,0x4c14,0x4c40,0x4ba8,0x4bba,0x4c32,0x4c12},
 'timing-live-map.i':{0x489a,0x489c,0x48a0,0x48a2,0x48b0,0x48b2,0x44dc,0x475a},
 'timing-live-render.i':{0x468c,0x468e},
 'timing-live-target-view.i':{0x468c,0x46a4,0x46a6},
 'timing-world-commands.i':{0x4ed4},
 'timing-boundary-command.i':{0x4ed4},
 'timing-runtime.i':{0x475a,0x475c,0x4760,0x4762,0x1068},
 'timing-runtime-target.i':{0x46de},
 'timing-runtime-target-view.i':{0x468c},
}
# Tables whose third field is an original address; second is its hunk.
tables={'timing-target-select.i','timing-target-collect.i','timing-actor-preview.i','timing-script-preview.i','timing-scene-private.i'}
pairs={'timing-world-tail.i','timing-world-periodic.i','timing-world-damage.i','timing-field-guidance.i','timing-scene-target.i'}
skip={'timing-input.i','timing-runtime-forecast.i','timing-forecast-sine.i','timing-world-reserves.i','timing-live-actor-generation.i'}
used=set();changed=[]
for p in src.glob('timing-*.i'):
 if p.name in skip:continue
 lines=p.read_text().splitlines();out=[]
 for l in lines:
  code,sep,comment=l.partition(';');matches=list(re.finditer(r'\$([0-9a-fA-F]+)',code));selected=[]
  dc=re.match(r'\s*dc\.w\s+(.*)',code,re.I)
  if dc:
   fields=dc[1].split(',');indices=[]
   if p.name in tables and len(fields)==4 and fields[1].strip()=='0':indices=[2]
   if p.name in pairs:
    if not (p.name=='timing-field-guidance.i' and '$50f9' in code):indices=list(range(1,len(fields),2))
   if p.name=='timing-visibility-raster.i':indices=[i+2 for i in range(0,len(fields),3) if fields[i+1].strip()=='0']
   if p.name=='timing-actor-preview.i' and len(fields)==3:indices=[0]
   for i in indices:
    fields[i]=re.sub(r'\$([0-9a-fA-F]+)',lambda m:'GS0_'+m[1].lower().zfill(4),fields[i]);used.update(int(m[1],16) for m in re.finditer(r'GS0_([0-9a-f]+)',fields[i]))
   if indices:code=code[:dc.start(1)]+','.join(fields)
  else:
   for m in matches:
    n=int(m[1],16)
    # Skip instruction words, masks and geometry values, retaining address operands.
    is_native=(0x5400<=n<=0xf0c8 or n in low.get(p.name,set()))
    if not is_native:continue
    prefix=code[:m.start()]
    if re.match(r'\s*(cmpi|move)\.[bwl]\s+#$',prefix,re.I):continue
    if re.match(r'\s*(andi|ori|eori)\.',code,re.I):continue
    if 'equ' in code.lower() and len(matches)==1:continue
    if n in (0x7fff,0x8000,0xd800):continue
    selected.append(m);used.add(n)
   for m in reversed(selected):code=code[:m.start()]+'GS0_'+m[1].lower().zfill(4)+code[m.end():]
  nl=code+sep+comment;out.append(nl)
  if nl!=l:changed.append((p.name,l,nl))
 p.write_text('\n'.join(out)+'\n')
# One skipped file mixes a short opcode signature table with code addresses.
p=src/'timing-live-actor-generation.i';s=p.read_text()
for n in (0xba08,0xbea8):s=s.replace(f'${n:x}',f'GS0_{n:04x}');used.add(n)
p.write_text(s)
blocks=json.loads(Path('tmp/analysis/ntsc-normalized-blocks.json').read_text())
def mapped(n):
 for a,b,size in blocks:
  if a<=n<a+size:return n+b-a
 before=[(a,b,size) for a,b,size in blocks if a+size<=n]
 after=[(a,b,size) for a,b,size in blocks if a>n]
 if before and after and before[-1][1]-before[-1][0]==after[0][1]-after[0][0]:return n+before[-1][1]-before[-1][0]
 print('AMBIGUOUS',hex(n),before[-1:] ,after[:1]);return n+(min(blocks,key=lambda v:min(abs(v[0]-n),abs(v[0]+v[2]-n)))[1]-min(blocks,key=lambda v:min(abs(v[0]-n),abs(v[0]+v[2]-n)))[0])
out=['; Native code-hunk addresses for the 0658 and 1489 executables.', '; Hunk 6/player field offsets are shared and are not translated here.',' IFD GUNSHIP_NTSC']
for n in sorted(used):out.append(f'GS0_{n:04x} equ ${mapped(n):04x}')
out+=[' ELSE']
for n in sorted(used):out.append(f'GS0_{n:04x} equ ${n:04x}')
out+=[' ENDC']
(src/'timing-offsets.i').write_text('\n'.join(out)+'\n')
Path('tmp/analysis/ntsc-offset-edits.txt').write_text('\n'.join(f'{p}: {a}\n -> {b}' for p,a,b in changed))
print('native offsets',len(used),'lines',len(changed))
