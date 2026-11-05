from pathlib import Path
from PIL import Image
import json,hashlib
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'
rows=[]
for k in (1,2):
 def im(n):return Image.open(p/n/f'frame-{k}.png').convert('RGB')
 a=im('c4-colour-r2-frameprobe2-85-a500-candidate-images');b=im('c4-colour-r2-frameprobe2-170-a500-candidate-images');c=im('c4-colour-r2-v2-heavy-v2-a500-candidate-images');d=im('c4-colour-r2-v2-heavy-v2-a500-baseline-render-images')
 s={(x,y) for y in range(a.height) for x in range(a.width) if a.getpixel((x,y))!=b.getpixel((x,y))}
 f={(x,y) for y in range(a.height) for x in range(a.width) if c.getpixel((x,y))!=d.getpixel((x,y))}
 assert s=={(x,y) for y in range(576) for x in range(754) if x>=752 or y>=574}
 assert all(a.getpixel(q)==(85,85,85) and b.getpixel(q)==(170,170,170) for q in s)
 assert not f-s
 assert all(a.getpixel((x,y))==c.getpixel((x,y)) for y in range(576) for x in range(754) if (x,y) not in s)
 rows.append(dict(frame=k,unrendered_pixels=len(s),original_mismatch_pixels=len(f),rendered_pixel_differences=0))
out=dict(status='passed',scope='Two sentinel colours filled before next profiled field, with contents-lost notification. All original mismatches lie in untouched host buffer padding. Rendered pixels unchanged. No crop/mask; corrected capture initializes whole host buffer to zero before field, compares full 754x576 RGB.',rows=rows,benchmark_sha256=hashlib.sha256((r/'tmp/step3/fs-uae').read_bytes()).hexdigest(),observer_sha256=hashlib.sha256((r/'tmp/step5-frame-observer-build/fs-uae').read_bytes()).hexdigest())
(r/'manifest/step5-c4-r2-frame-padding.json').write_text(json.dumps(out,indent=2)+'\n')
print(out)
