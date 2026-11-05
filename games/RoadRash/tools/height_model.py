import json,struct,sys,math
from pathlib import Path
root=Path('tmp')
def signedword(x):return (x+32768)%65536-32768
def mulfrac(v,f,rounding=False):
 q=(abs(v)*f+(32768 if rounding else 0))//65536
 return -q if v<0 else q
def heights(track,cam,height,correct=False):
 s=cam>>16;f=cam&65535
 slope=track[((s+int(correct))&255)*2+1]
 d3=-mulfrac(slope,f);h=[]
 for j in range(32):
  h.append(height-d3);d3+=track[((s+j+1)&255)*2+1]
 return h
for tag in sys.argv[1:]:
 p=root/('h1-'+tag)
 if not (p/'trace.json').exists():continue
 track=struct.unpack('>512b',(p/'track.bin').read_bytes());r=json.load(open(p/'trace.json'));out=[]
 for row in r:
  track=struct.unpack('>512b',bytes.fromhex(row['track'])) if 'track' in row else track
  b=bytes.fromhex(row['state']);w=lambda o:struct.unpack_from('>h',b,o)[0];l=lambda o:struct.unpack_from('>I',b,o)[0]
  cam=l(0x1e);pos=l(0x64);geom=bytes.fromhex(row['geometry']);actual=[struct.unpack_from('>h',geom,4*j+2)[0] for j in range(32)]
  h=heights(track,cam,l(0x1a),correct="fix" in tag);assert h==actual,(tag,row['field'],h,actual)
  def rider(h):
   j=(pos>>16)-(cam>>16);f=pos&65535;z=((pos-cam)>>8)+256
   interp=h[j]-mulfrac(h[j]-h[j+1],f,True)-w(0x92)
   y=max(1,76+math.trunc(interp*256/z))
   if b[0xc8]&8:y|=w(0x72)&3
   return y
  def road(h):
   ys=[signedword(76+math.trunc(v*256/(256+j*256-((cam&65535)>>8)))) for j,v in enumerate(h)]
   return [max(1,y) if v<0 else y for v,y in zip(h,ys)]
  ry=list(struct.unpack('>32h',bytes.fromhex(row['road_y'])));assert road(h)==ry,(tag,row['field'],road(h),ry)
  obj=bytes.fromhex(row['objects']);player=next((struct.unpack_from('>h',obj,i+2)[0] for i in range(0,len(obj),20) if struct.unpack_from('>H',obj,i+8)[0]&0x8000),None)
  assert player is None or rider(h)==player,(tag,row['field'],rider(h),player)
  new=heights(track,cam,l(0x1a),True)
  out.append(dict(field=row['field'],segment=cam>>16,fraction=cam&65535,camera_height=l(0x1a),air=w(0x92),slope=track[((cam>>16)&255)*2+1],next_slope=track[(((cam>>16)+1)&255)*2+1],y=player,candidate_y=rider(new),road=ry,candidate_road=road(new)))
 (p/'model.json').write_text(json.dumps(out,indent=2));print(tag,'exact matches:',len(out),'frames')
 for a,b in zip(out,out[1:]):
  if a['segment']!=b['segment'] and 40<=b['segment']<=52:print(a['field'],b['field'],a['segment'],b['segment'],'slope',a['slope'],b['slope'],'Y',a['y'],b['y'],'candidate',a['candidate_y'],b['candidate_y'])
