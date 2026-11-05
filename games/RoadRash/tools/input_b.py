import json,os,sys
from harness_a import *
os.environ.setdefault('SLAVE',str(ROOT/'tmp/build/RoadRash.slave'))
s=Session(sys.argv[1]);evidence=[]
def state(label):
    v=dict(label=label,field=field(s),steering=rd(s,0xa7262,2),pause=rd(s,0xa7208,2),key=read_bytes(s,0xae969,1).hex())
    evidence.append(v);print(v,flush=True);return v
try:
    if os.environ.get('RR_PAD'):s.input('JOY2_CD32_PLAY',0)
    route(s);state('initial')
    s.input('JOY2_RIGHT',1);s.cmd('monitor fields 19');a=state('steer')
    s.input('JOY2_RIGHT',0);s.cmd('monitor fields 39');b=state('released')
    assert a['steering']!=0 and b['steering']==0
    for label in ['pause','resume']:
        s.input('JOY2_CD32_PLAY',1) if os.environ.get('RR_PAD') else s.cmd('monitor key 40 1');s.cmd('monitor fields 9');s.input('JOY2_CD32_PLAY',0) if os.environ.get('RR_PAD') else s.cmd('monitor key 40 0');s.cmd('monitor fields 9');c=state(label)
        assert c['pause']==(1 if label=='pause' else 0)
        if label=='pause':
            s.cmd('monitor fields 19');assert state('still paused')['field']==c['field']
    if os.environ.get('RR_STACK_TEST'):
        from stack_probe_c import stack_probe
        (s.out/'stack.json').write_text(json.dumps(stack_probe(s)))
    (s.out/'input.json').write_text(json.dumps(evidence,indent=2))
finally:s.quit()
