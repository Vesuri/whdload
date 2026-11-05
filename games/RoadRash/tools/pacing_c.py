"""Read and verify real 68k pacing decisions, including a forced-load build."""
import json,os,struct,sys
from harness_a import *
def c_records(s):
    target=rd(s,0x87738)
    data=read_bytes(s,target,2048);offset=data.find(b'RRCSTAT1')
    if offset<0:raise RuntimeError('missing C diagnostic marker')
    addr=target+offset;head=read_bytes(s,addr,16);count,resets=struct.unpack_from('>II',head,8)
    if not 0<count<=2048:raise RuntimeError(count)
    data=read_bytes(s,addr+16,count*8)
    return dict(resets=resets,records=[dict(field=f,required=r,selected=n) for f,r,n in struct.iter_unpack('>IHH',data)])
def validate(data):
    history=[];current=2;streak=0;changes=[]
    for i,row in enumerate(data['records']):
        requirement=row['required'];history=(history+[requirement])[-8:];candidate=max(2,*history)
        if candidate>current:expected=candidate;streak=0
        else:
            streak=streak+1 if requirement<current else 0
            expected=candidate if streak>=32 else current
            if expected!=current:streak=0
        assert row['selected']==expected,(i,row,current,streak,expected)
        if expected!=current:changes.append(dict(frame=i,field=row['field'],old=current,new=expected))
        current=expected
    return changes
if __name__=='__main__':
    s=Session(sys.argv[1])
    try:
        route(s);s.input('JOY2_UP',1);advance(s,1000)
        data=c_records(s);data['changes']=validate(data);data['provenance']=provenance(os.environ['SLAVE'],s)
        data['stats']=counters(s,stats_address(s));data['b_stats']=b_counters(s)
        (s.out/'pacing.json').write_text(json.dumps(data,indent=2)+'\n')
        print('records',len(data['records']),'changes',data['changes'],flush=True)
        if os.environ.get('RR_C_STRESS'):
            assert [(v['frame'],v['new']) for v in data['changes']]==[(40,3),(41,4),(73,2),(100,3),(120,4),(152,2)]
    finally:s.quit()
