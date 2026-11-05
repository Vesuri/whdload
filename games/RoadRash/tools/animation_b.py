import json,os,sys,struct
from harness_a import *
os.environ.setdefault('SLAVE',str(ROOT/'tmp/build/RoadRash-verify.slave'))
os.environ['WHD_ARGS']=os.environ.get('WHD_ARGS','')+' CUSTOM2=1'
s=Session(sys.argv[1])
try:
    initial=route(s);target=rd(s,0x89d34);data=read_bytes(s,target,256);offset=data.find(b'RRANIM01');assert offset>=0
    address=target+offset;stats=stats_address(s);before=counters(s,stats);values=[]
    s.input('JOY2_UP',1)
    for t in range(102,602,2):
        if t in (200,400,600):s.shot(f'race-{t:04d}.png')
        else:advance(s,t)
        f,p=struct.unpack('>II',read_bytes(s,address+8,8));assert p==(f>>2)&7
        values.append([t,f,p])
    after=counters(s,stats)
    result=dict(provenance=provenance(os.environ['SLAVE'],s),values=values,fps=(after['frames']-before['frames'])/10,histogram=[y-x for x,y in zip(before['histogram'],after['histogram'])])
    (s.out/'animation.json').write_text(json.dumps(result,indent=2));print('fps',result['fps'],flush=True)
finally:s.quit()
