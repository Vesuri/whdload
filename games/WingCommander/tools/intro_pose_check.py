#!/usr/bin/env python3
"""Native rendering from captured intro worlds: intermediate motion and restoration."""
import argparse,hashlib,json,mmap,re,struct
from pathlib import Path
from timing_audit_check import CPU
from cd32_runtime import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if (ROOT/'tmp').resolve() not in a.output.resolve().parents or a.output.exists():raise ValueError('new tmp output required')
    meta=json.loads((a.capture/'result.json').read_text());build=json.loads((a.build/'build.json').read_text())
    assert meta['complete'] and meta['fixture']['sha256']==build['sha256']
    assert hashlib.sha256((a.build/'WingCommanderCD32.Slave').read_bytes()).hexdigest()==build['sha256']
    sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    layout=meta['layout'];s=layout['slave'];size=0xfda0;results=[]
    with (a.capture/'states.bin').open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as states:
        assert len(states)%size==0
        groups={k:[] for k in ('title','credits')}
        for i in range(len(states)//size):
            credit=struct.unpack_from('>H',states,i*size+0x3892)[0]
            groups['credits' if credit else 'title'].append(i)
        for model in (2,4):
            for group,indices in groups.items():
                assert len(indices)>100
                memory=(a.capture/('title-ready-fast.bin' if group=='title' else 'credits-start-fast.bin')).read_bytes()
                c=CPU(memory,layout,model)
                def put(n,f,v):c.write(s+sy[n],struct.pack('>'+f,v))
                def run(n):c.run(s+sy[n]-c.code)
                # Exercise all native E:02e4 drawing; exclude composition/c2p/
                # publication, which require the live DMA/IRQ environment.
                c.write(c.code+0xc40,bytes.fromhex('4e75'))
                put('intro_active','H',1);put('timing_active','H',0);put('release_pending','H',0)
                # No diagnostic memory writes are needed for native semantics.
                c.write(s+sy['frame_stat'],bytes.fromhex('4e75'))
                projected=0;pose_moves=0;renders=0
                # First page only for credits, before later asset/script changes.
                population=indices if group=='title' else indices[:240]
                for at in (len(population)//6,len(population)//3,len(population)//2):
                    index=population[at];row=states[index*size:(index+1)*size]
                    c.write(c.data,row);put('timing_scene_valid','H',0)
                    run('timing_scene_snapshot');run('timing_scene_snapshot')
                    previous=None
                    for fraction in (0,10,20,30,40):
                        c.write(c.data,row)
                        put('timing_clock','I',c.data_value(0x7f02,'I'));c.write(s+sy['timing_clock']+4,struct.pack('>I',fraction));put('timing_hz','I',50)
                        before=c.read(c.data,size);run('intro_draw');shown=c.read(c.data,size)
                        run('intro_finish');after=c.read(c.data,size)
                        for off in (0x919a,0xa148,0xb450,0xb750,0x9d6c):assert after[off:off+768]==before[off:off+768],(model,group,index,hex(off))
                        for off,length in ((0x96fe,128),(0x97f6,128),(0x94c6,128),(0x9578,384),(0x6f18,4),(0x914c,2)):
                            assert after[off:off+length]==before[off:off+length],(model,group,index,hex(off))
                        if previous:
                            for slot in range(62):
                                if shown[0x919a+12*slot:0x91a6+12*slot]!=previous[0x919a+12*slot:0x91a6+12*slot]:pose_moves+=1
                                kind=struct.unpack_from('>h',row,0x96fe+2*slot)[0]
                                xy=lambda b:(struct.unpack_from('>h',b,0xa45c+2*slot)[0],struct.unpack_from('>h',b,0xabe8+2*slot)[0])
                                old,new=xy(previous),xy(shown)
                                if slot<61 and kind>=3 and kind!=7 and old[0]!=-32767 and new[0]!=-32767 and old!=new:projected+=1
                        previous=shown;renders+=1
                c.close()
                assert projected and pose_moves,(model,group,projected,pose_moves)
                results.append(dict(model=model,section=group,renders=renders,between_tick_pose_moves=pose_moves,between_tick_projected_moves=projected,restored=True))
    a.output.write_text(json.dumps(dict(passed=True,results=results,scope='native E:02e4 rendering from live authoritative states; composition/publication excluded; not FPS'),indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
