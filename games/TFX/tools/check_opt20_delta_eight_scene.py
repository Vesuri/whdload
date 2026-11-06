import json,struct,sys
from pathlib import Path
import replay_flight
from amigaxdev import barto
r=Path(sys.argv[1]);a=r/'delta-eight-scene-off';b=r/'delta-eight-scene-on'
images=[]
for n in [1,10,30,45,57]:
 planes=[]
 for p in [a,b]:
  t=barto.load(p/f'swap-{n:03d}.trace');pub=json.loads((p/'publications.json').read_text())[n-1];c=pub['copper'];words=dict(struct.unpack_from('>HH',t.chip,o) for o in range(c,c+192,4));ptr=[words[0xe0+4*i]*65536+words[0xe2+4*i] for i in range(8)];planes.append(b''.join(t.chip[o:o+8000] for o in ptr))
 same=planes[0]==planes[1];png=(a/f'swap-{n:03d}.png').read_bytes()==(b/f'swap-{n:03d}.png').read_bytes();assert same and png
 images.append(dict(swap=n,planes_equal=same,png_equal=png))
(r/'delta-eight-scene-comparison.json').write_text(json.dumps(images,indent=2));print(images)
