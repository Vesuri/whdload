"""Read-only debugger inspection of the compiled guest visibility twin."""
import json,sys,struct,re,os
from pathlib import Path
from gunship import Session,machine
from route import run
from flight_profile import ROUTE
root=Path(__file__).resolve().parents[1]
listing=Path(os.environ.get('PROBE_LISTING',str(root/'tmp/c/visibility-probe.lst'))).read_text(encoding='latin1')
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
s=Session(sys.argv[1],dict(EXTRA_ARGS=machine().get('EXTRA_ARGS','')+' --video_driver=null',WHD_ARGS='CUSTOM1=1 CUSTOM2=12345'))
try:
 run(s,ROUTE)
 mem=s.read(0x200000,0x800000);hits=[];pos=0
 while True:
  pos=mem.find(b'GSVP0001',pos)
  if pos<0:break
  words=struct.unpack_from('>9I',mem,pos+8)
  if all(0x200000<a<0xa00000 for a in words[:2]):hits.append((0x200000+pos,words))
  pos+=8
 assert len(hits)==1,hits
 marker,words=hits[0]
 while words[3]!=100 and words[3]<0x80000000:
  s.cmd('maintenance flush register-cache')
  print('pending',dict(stage=words[3],completed=words[4],pc=s.regs()),flush=True)
  s.fields(200)
  words=struct.unpack('>9I',s.read(marker+8,36))
 h0,h6,buffer,status,completed,nonempty,bitmap,plane_bytes,depth=words
 report=dict(marker=marker,h0=h0,h6=h6,buffer=buffer,status=status,completed=completed,nonempty=nonempty,bitmap=bitmap,plane_bytes=plane_bytes,depth=depth)
 print('guest',report,flush=True)
 base=marker-sym('vp_result')
 for name,n in [('vp_result',44),('vp_expected',168),('vp_target',546)]:
  (s.out/(name+'.bin')).write_bytes(s.read(base+sym(name),n))
 (s.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 if os.environ.get('PROBE_HEADING_FAILURE'):
  assert status==0xfffffff9 and completed<16,report
  print('PASS wrong-heading negative control rejected',flush=True)
  sys.exit(0)
 if os.environ.get('PROBE_PANEL_FAILURE'):
  assert status==0xfffffff7 and completed==0,report
  print('PASS intentional panel bitmap corruption rejected',flush=True)
  sys.exit(0)
 if os.environ.get('PROBE_EXPECT_FAILURE'):
  assert status==0xfffffff9 and completed==0,report
  print('PASS intentional bitmap corruption rejected',flush=True)
  sys.exit(0)
 assert status==100 and completed==16 and nonempty>0,report
 # The guest compared all actual bitplanes. Retain its final reference bitmap.
 planes=s.read(buffer+64000,plane_bytes*depth);(s.out/'reference-planes.bin').write_bytes(planes)
 desc=s.read(bitmap,40);(s.out/'bitmap-descriptor.bin').write_bytes(desc)
 row_size=184 if os.environ.get('PROBE_TIMING') else 176
 rows=s.read(buffer+128000,16*row_size);views=[]
 (s.out/'vp_rows.bin').write_bytes(rows)
 for i in range(16):
  row=rows[i*row_size:(i+1)*row_size];count=int.from_bytes(row[2:4],'big')
  views.append(dict(heading=(i%8)*32,mode=i//8,count=count,pixels=list(row[168:168+count])))
  if os.environ.get('PROBE_OWNER'):
   views[-1].update(target_status=row[0],selected_identity=int.from_bytes(row[4:6],'big'),selected_subtype=int.from_bytes(row[6:8],'big'),sample_bytes=list(row[168:174]))
  if row_size==184:views[-1]['eclocks']=list(struct.unpack_from('>II',row,176))
 # Independently decode the final view's saved native bitplanes at its samples.
 row=rows[-row_size:];stride=int.from_bytes(desc[:2],'big')
 for i in range(0 if os.environ.get('PROBE_PANEL') else views[-1]['count']):
  x=int.from_bytes(row[0x80+2*i:0x82+2*i],'big');y=int.from_bytes(row[0x8a+2*i:0x8c+2*i],'big')
  pixel=sum(((planes[j*plane_bytes+y*stride+x//8]>>(7-x%8))&1)<<j for j in range(depth))
  assert pixel==row[168+i],(x,y,pixel,row[168+i])
 if row_size==184:
  calibration,overhead=struct.unpack('>II',s.read(base+sym('vp_calibration'),8))
  assert 120000<calibration<160000 and 0<overhead<100,(calibration,overhead)
  report['calibration_10_fields']=calibration;report['empty_timer_eclocks']=overhead
  for v in views:
   assert min(v['eclocks'])>overhead
   v['field_equivalents']=[10*(n-overhead)/calibration for n in v['eclocks']]
  report['mean_ms_at_nominal_50Hz']=[sum(v['field_equivalents'][i]*20 for v in views)/16 for i in range(2)]
 if os.environ.get('PROBE_PANEL'):
  report['panel_passes']=int.from_bytes(s.read(base+sym('vpp_passes'),4),'big')
  assert report['panel_passes']==16,report
 report['views']=views;report['status']='passed'  
 (s.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS',views,flush=True)
finally:s.quit()
