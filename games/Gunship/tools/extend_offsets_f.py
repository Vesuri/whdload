from pathlib import Path
import re,json
src=Path('src');p=src/'timing-offsets.i'
s=p.read_text();parts=s.split(' ELSE\n');pal=parts[1];ntsc=parts[0]
blocks=json.loads(Path('tmp/analysis/ntsc-normalized-blocks.json').read_text())
def add(n):
 global pal,ntsc
 key=f'GS0_{n:04x}'
 if key in pal:return key
 hit=[(a,b,z) for a,b,z in blocks if a<=n<a+z]
 if not hit:
  bef=[x for x in blocks if x[0]+x[2]<=n][-1];aft=[x for x in blocks if x[0]>n][0]
  assert bef[1]-bef[0]==aft[1]-aft[0],hex(n)
  hit=[bef]
 a,b,z=hit[0];ntsc+=f'{key} equ ${n+b-a:04x}\n';pal=f'{key} equ ${n:04x}\n'+pal
 return key
repls={'timing-world-reserves.i':[0x7f80,0x590c], 'timing-live-map.i':[0x48a6,0x48aa,0x48ae], 'timing-runtime.i':[0x487a], 'timing-scene-private.i':[0x5a24]}
for fn,ns in repls.items():
 p=src/fn;s=p.read_text()
 for n in ns:s=re.sub(r'\$0*'+f'{n:x}'+r'\b',add(n),s,flags=re.I)
 if 'include "timing-offsets.i"' not in s:s=' include "timing-offsets.i"\n'+s
 p.write_text(s)
# Decoder shrinks by 12 bytes; internal tail references follow its own endpoints.
p=src/'timing-world-commands.i';s=p.read_text()
for old,a,b in [('$462',0x5336,0x4ed4),('$3f8',0x52cc,0x4ed4),('$426',0x52fa,0x4ed4)]:s=s.replace('equ '+old,'equ '+add(a)+'-'+add(b))
p.write_text(s)
p=src/'timing-boundary-command.i';s=p.read_text().replace('$460(a0)',add(0x5334)+'-'+add(0x4ed4)+'(a0)');p.write_text(s)
# Weapons has four extra bytes after the first fire branch.
p=src/'timing-world-weapons.i';s=p.read_text().replace('equ $3fe','equ '+add(0x9b9a)+'-'+add(0x979c))
# Every relative offset at/after PAL +9828 refers to the shifted tail.
for m in reversed(list(re.finditer(r'\$([0-9a-fA-F]+)',s))):
 n=int(m[1],16)
 if 0x8c<=n<0x3fe and ';' not in s[s.rfind('\n',0,m.start())+1:m.start()]:s=s[:m.start()]+'('+add(0x979c+n)+'-'+add(0x979c)+')'+s[m.end():]
p.write_text(s)
(src/'timing-offsets.i').write_text(ntsc+' ELSE\n'+pal)
