from pathlib import Path
import json
from PIL import Image,ImageChops
root=Path(__file__).resolve().parents[1]/'tmp';ref=root/'c-fused-lean-state-v2';x=json.loads((ref/'step.json').read_text());regions=[(0xa5d60,0x1180),(0xa5d50,16),(0xa5d1e,4),(0xa5d22,4),(0xa7220,8),(0xa59f4,2)]
for mode in ['fixed','period1','period2','period3','vary','pattern']:
 p=root/('c-raster-edge-'+mode+'-state');y=json.loads((p/'step.json').read_text());count=min(x['steps'],y['steps'])-1
 assert (ref/'hashes.bin').read_bytes()[4:(count+1)*4]==(p/'hashes.bin').read_bytes()[4:(count+1)*4]
 assert x['sound_events']==y['sound_events']
 a=(ref/'step1457.bin').read_bytes();b=(p/'step1457.bin').read_bytes()
 for addr,size in regions:assert a[addr-0xa5900:addr-0xa5900+size]==b[addr-0xa5900:addr-0xa5900+size],hex(addr)
 image_ref=ref if mode=='fixed' else root/('c-fused-lean-'+mode)
 pixels=None
 if (image_ref/'final.png').exists():
  a=Image.open(image_ref/'final.png').convert('RGB');b=Image.open(p/'final.png').convert('RGB');pixels=a.size==b.size and ImageChops.difference(a,b).getbbox() is None
 result=dict(common_hashes=count,sound_equal=True,six_ranges_equal=True,histogram=y['frame_stats']['histogram'],final_pixels_equal=pixels,comparison_image=str(image_ref/'final.png') if pixels is not None else None)
 (p/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(mode,'hashes',count,'pixels',pixels,'cadences',[(i,v) for i,v in enumerate(result['histogram']) if v])
