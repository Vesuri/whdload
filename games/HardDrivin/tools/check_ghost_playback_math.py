import json,os,shutil,struct,sys
from capture_demo import ROOT
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof'/(sys.argv[1] if len(sys.argv)>1 else 's4-ghost-play-math');out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-ghost-play-math.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520);s.env['WHD_ARGS']+=' CUSTOM1=1'
cases=[([1000,2000,-3,700,-700,17],[1007,1991,4,-700,700,-16]),([65535,0,-32768,-700,720,-720],[0,65535,32767,700,-720,720]),([0,65535,32767,0,0,0],[65535,0,-32768,0,0,0]),([65534,65534,-5,720,5,5],[65535,65535,-5,-720,5,5]),([31,47,1,-720,-719,-1],[31,47,1,720,-720,1]),([20000,20100,500,359,100,200],[20001,20099,-501,-359,99,199])]
def trunc(n,d):return (abs(n)//d)*(-1 if n<0 else 1)
def pose(left,right,phase):
 values=[]
 for j,(x,y) in enumerate(zip(left,right)):
  if j<2:z=(x*(48-phase)+y*phase)//48
  elif j==2:z=trunc(x*(48-phase),48)+trunc(y*phase,48)
  else:
   if j==3 and abs(x-y)>720:x+=1440 if x<0 else -1440
   z=trunc(x*(48-phase)+y*phase,48)
  values.append(z&65535)
 return [values[i] for i in [0,2,1,4,3,5]]
try:
 s.boot();hits=[]
 for _,b in s.dump_banks('ghost-play-math'):
  i=b.find(b'HDGHPMT1')
  if i>=0:hits.append(b[i+8:i+8+112+0x6930])
 assert len(hits)==1;raw=hits[0];meta=struct.unpack_from('>III',raw);assert meta==(0,36,288),meta
 for i,(left,right) in enumerate(cases):
  for phase in range(48):
   actual=list(struct.unpack_from('>6H',raw,112+0x4000+(i*48+phase)*12));expected=pose(left,right,phase);assert actual==expected,(i,phase,actual,expected)
 assert struct.unpack_from('>I',raw,12)[0]==1
 assert struct.unpack_from('>III',raw,16)==(56,48,2)
 assert raw[32:34]==bytes([1,255]) and struct.unpack_from('>I',raw,36)[0]==5
 assert raw[40:46]==bytes([255,0,255,60,7,0])
 assert struct.unpack_from('>6H',raw,48)==(1200,0,1000,0,0,0)
 assert struct.unpack_from('>III',raw,64)==(14304,14304,4)
 assert raw[80:82]==bytes([0,255]) and struct.unpack_from('>I',raw,84)[0]==7
 assert struct.unpack_from('>6H',raw,88)==(30000,500,50000,200,100,300)
 result=dict(passed=True,cases=6,phases=48,native_grid_comparisons=36,native_grid_mismatches=0,independent_model_poses=288,crossed_finish_sound_events=1,finish_checks=5,clamped_final_pose=True)
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
