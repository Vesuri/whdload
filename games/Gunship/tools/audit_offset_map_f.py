from pathlib import Path
from amitools.binfmt.BinFmt import BinFmt
import json,re,collections
r=Path('tmp/game');aa,bb=[BinFmt().load_image(str(r/p/'data/gamemule')) for p in ('Gunship','GunshipNTSC')]
a,b=[x.get_segments()[0] for x in (aa,bb)];ab=bytes(a.get_data());bbin=bytes(b.get_data())
blocks=json.loads(Path('tmp/analysis/ntsc-normalized-blocks.json').read_text());exact={}
for rel in a.get_reloc(a).get_relocs():
 pos=rel.offset
 hit=[(x,y,n) for x,y,n in blocks if x<=pos and pos+4<=x+n]
 if not hit:continue
 x,y,n=hit[0];old=int.from_bytes(ab[pos:pos+4],'big');q=pos+y-x;new=int.from_bytes(bbin[q:q+4],'big')
 exact.setdefault(old,collections.Counter())[new]+=1
p=Path('src/timing-offsets.i');s=p.read_text();ntsc,pal=s.split(' ELSE\n')
for old,c in exact.items():
 if len(c)>1:print('ambiguous target',hex(old),c);continue
 key=f'GS0_{old:04x}';m=re.search(r'^'+key+r' equ \$([0-9a-f]+)$',ntsc,re.M)
 if m and int(m[1],16)!=next(iter(c)):
  new=next(iter(c));print('correct',hex(old),m[1],hex(new));ntsc=ntsc[:m.start(1)]+f'{new:04x}'+ntsc[m.end(1):]
p.write_text(ntsc+' ELSE\n'+pal)
