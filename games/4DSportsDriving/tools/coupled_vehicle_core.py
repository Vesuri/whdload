"""Reusable scoped straight stock-car recurrence for controlled rate comparisons."""
import json,struct
from pathlib import Path
from copy import deepcopy
from drivetrain_model import step as engine
from contact_step import step as contact
from native_contact_response import rotate

def seed(cap):
    cap=Path(cap);m=json.loads((cap/'anchor.json').read_text());ram=(cap/'memory.bin').read_bytes();base=m['memory_base'];co=m['data_base']+0x7ffe-0x92e-base;p=ram.index(b'4DA4PHYS')+12
    read=lambda a,f:struct.unpack_from('>'+f,ram,a-base)[0]
    unpack=lambda fmt,data,off:list(struct.unpack_from('>'+fmt,data,off))
    car=bytearray(ram[co:co+208]);carry=dict(zip(('acceleration','distance','gear'),struct.unpack_from('>hHh',ram,p+2)))
    e=[m['simulation_tick']+1]+unpack('3h',car,0x18)+[0]*9+unpack('4h',car,0x54)+unpack('4h',car,0x6c)+unpack('4h',car,0x4c)
    e += [read(base+p+o+4*w,'h') for o in (8,10) for w in range(4)]
    e += unpack('4h',ram,p+24)+unpack('4h',ram,p+40)+unpack('h',ram,p+144)+unpack('3H',ram,p+132)+[0]*24
    assert len(e)==69
    state=dict(entry=e,position=unpack('3i',car,0),cached=[unpack('3h',car,0x74+6*w) for w in range(4)])
    # Fixed selected stock car, checked by the original live parameter pointer.
    assert m['data_base']==5689288
    return dict(car=car,carry=carry,contact=state),read,m['data_base']+0x79de

def advance(bundle,hz,read,param,solver=None,movement_matrix=None):
    car=bytearray(bundle['car']);car[0xc0]=sum(bool(v) for v in car[0xc4:0xc6]);car[0xc1]=sum(bool(v) for v in car[0xc2:0xc6])
    car,carry,eng=engine(car,bundle['carry'],param,read,hz=hz)
    state,rec=contact(bundle['contact'],hz,eng['distance'],body_solver=solver,movement_matrix=movement_matrix);out=rec['output']
    struct.pack_into('>h',car,0x1e,-rotate([0,0,130],rec['entry'][4:13])[1])
    for w,r in enumerate(out['wheels']):car[0xc2+w]=int(r['suspension_clearance']<=12)
    return dict(car=car,carry=carry,contact=state),dict(engine=eng,contact=rec)

def summarize(b):
    w=lambda o:struct.unpack_from('>H',b['car'],o)[0]
    return dict(position=b['contact']['position'],pitch=b['contact']['entry'][2],speed=w(0x2a),target=w(0x2c),rpm=w(0x22),gear=b['car'][0xbe],clutch=b['car'][0xca],flags=list(b['car'][0xc2:0xc6]))
