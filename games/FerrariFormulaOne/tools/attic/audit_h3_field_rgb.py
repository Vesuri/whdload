from pathlib import Path
import gzip,sys,io,json,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
from PIL import Image
r=Path(__file__).resolve().parents[1];result={}
for arm in ['control','candidate']:
 p=r/f'tmp/step5/c4-q03-render-profile-a1200-fast-h3-matched-{arm}';path=p/'detail.bin';path.write_bytes(gzip.decompress((p/'detail.bin.gz').read_bytes()));t=barto.load(path);rows=[];seq=[]
 for f in t.fields:
  im=Image.open(io.BytesIO(f.shot)).convert('RGB');h=hashlib.sha256(im.tobytes()).hexdigest();rows.append(dict(field=f.index,sha256=h))
  if 0<f.index<47 and (not seq or seq[-1]!=h):seq.append(h)
 result[arm]=dict(fields=rows,compact=seq);path.unlink()
result['interior_sequences_exact']=result['control']['compact']==result['candidate']['compact'];(r/'manifest/render-h3-field-rgb.json').write_text(json.dumps(result,indent=2)+'\n');print('Field JPEG decoded RGB sequences:',len(result['control']['compact']),len(result['candidate']['compact']),'exact',result['interior_sequences_exact'])
