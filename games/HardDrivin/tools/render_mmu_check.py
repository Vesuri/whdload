from pathlib import Path
import json,struct,sys
from PIL import Image
from machine_profiles import banks
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());images=[(b,(p/('after-'+n+'.bin')).read_bytes()) for n,b,z in banks(m['configuration'])]
def read(a,n):return next(v[a-b:a-b+n] for b,v in images if b<=a and a+n<=b+len(v))
a4=m['layout']['a4'];front=struct.unpack('>I',read(a4-0x6a0e,4))[0];palptr=struct.unpack('>I',read(a4-0x7036,4))[0];b=read(front,32000);colors=struct.unpack('>16H',read(palptr,32));palette=[tuple(((c>>s)&15)*17 for s in [8,4,0]) for c in colors];im=Image.new('RGB',(320,200));im.putdata([palette[sum(((b[k*8000+y*40+x//8]>>(7-x%8))&1)<<k for k in range(4))] for y in range(200) for x in range(320)]);im.resize((640,400),Image.Resampling.NEAREST).save(p/'cockpit.png');assert len(set(im.getdata()))>=4
old=(p/'game-code.bin').read_bytes();base=m['layout']['code_base'];assert read(base,len(old))==old
r=json.loads((p/'functional-only.json').read_text());r.update(game_code_unchanged=True,nonblank_planar_output=True);(p/'functional-only.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
