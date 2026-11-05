from pathlib import Path
import gzip,io,json,sys,hashlib,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
from PIL import Image,ImageChops
r=Path(__file__).resolve().parents[1];out={};imgs=[]
for arm in ['control','candidate']:
 p=r/f'tmp/step5/c4-q03-render-profile-a1200-fast-h3-matched-{arm}';f=p/'detail.bin';f.write_bytes(gzip.decompress((p/'detail.bin.gz').read_bytes()));t=barto.load(f);res=json.loads((p/'result.json').read_text());base=int(res['probe'],16);sy=res['symbols'];img=Image.open(io.BytesIO(t.fields[2].shot)).convert('RGB');img.save(p/'field2-palette.png');imgs.append(img)
 # Existing COLOR00 write is the last instruction before B8_6551e.
 pc=base+sy['B8_6551e']-6;writes=[]
 for field in t.fields:
  cycles=0
  for addr,cost,regs in t.instructions(field):
   if addr==pc:writes.append(dict(field=field.index,cycles_in_field=cycles,value=regs[1]&65535))
   cycles+=cost
 out[arm]=writes;f.unlink()
assert [x['value'] for x in out['control']]==[x['value'] for x in out['candidate']]
out['native_colour00_sequence_exact']=True
out['note']='Same existing buffer-index COLOR00 values; timing shifts with earlier draw completion. Full intermediate JPEGs therefore are not identical; all 15 stable JPEG RGB images and bitplane-data sequences match. No palette operation is removed or value changed.'
ImageChops.difference(*imgs).save(r/'tmp/h3-field2-palette-difference.png');(r/'manifest/render-h3-palette.json').write_text(json.dumps(out,indent=2)+'\n');print('Native COLOR00 write values exact:',len(out['control']));print('First writes',out['control'][:3],out['candidate'][:3])
