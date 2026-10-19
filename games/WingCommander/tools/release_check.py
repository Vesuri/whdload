#!/usr/bin/env python3
"""Native release options/cache contract and integrated nonflight conversion."""
import argparse,hashlib,json,random,re,struct,subprocess,sys
from pathlib import Path
from cd32_runtime import ROOT
from c2p_check import CPU,BASE,STACK,STOP,ck,u,reference

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--negative-controls',action='store_true')
    p.add_argument('--sabotage',choices=('mode-map','nonflight-unlimited','flight-limited'),help=argparse.SUPPRESS)
    a=p.parse_args()
    out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp report required')
    meta=json.loads((a.build/'build.json').read_text());blob=(a.build/'payload.bin').read_bytes()
    slave=(a.build/'WingCommanderCD32.Slave').read_bytes()
    assert slave[32:-4]==blob and hashlib.sha256(slave).hexdigest()==meta['sha256']
    assert meta['release'] and meta['version']=='2.0b' and not meta['verify_only']
    sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    assert not any(n in sy for n in ('flight_verified','render_verified','timing_verify_schedule','frame_stat'))
    for off,key in ((0x24,'release_name'),(0x28,'release_info'),(0x32,'release_config')):assert struct.unpack_from('>H',blob,off)[0]==sy[key]
    assert b'$VER: WingCommanderCD32 2.0b (19.10.2026)\0' in blob
    if a.sabotage:
        changed=bytearray(blob)
        if a.sabotage=='mode-map':
            at=blob.index(bytes.fromhex('20bc00000003'),sy['release_setcpu'],sy['release_limit'])
            changed[at+5]=0
        elif a.sabotage=='nonflight-unlimited':
            changed[sy['release_limit']:sy['release_limit']+2]=bytes.fromhex('4e75')
        else:
            at=sy['release_limit']+4
            assert blob[at]==0x66
            changed[at:at+4]=bytes.fromhex('4e714e71')  # remove the flight bypass
        blob=bytes(changed)
    options=[]
    for model,flags in ((2,2),(4,8)):
        for custom in (0,1,2,3,4,5,0xffffffff):
            for pace in (0,1,2,3,4,5,0xffffffff):
                for policy in (0,256):
                    c=CPU(blob,model);c.write(BASE+0x1de4,struct.pack('>I',custom));c.write(BASE+0x1e04,struct.pack('>I',pace))
                    c.write(BASE+0x121e,struct.pack('>I',0x80000));c.write(4,struct.pack('>I',0x2000));c.write(0x2128,struct.pack('>H',flags))
                    # Record requested value/mask, return effective policy.
                    c.write(0x80060,bytes.fromhex('23c00003000023c100030004203c')+struct.pack('>I',policy)+bytes.fromhex('4e75'))
                    c.write(0x80004,bytes.fromhex('4ef900001000'));c.write(STACK,struct.pack('>I',STOP));c.reg(8,STACK);c.reg(3,0x80000)
                    c.reg(9,0x32a);c.reg(10,0x7f3f);c.reg(11,0x7654)
                    ck(u.uc_emu_start(c.h,BASE+sy['release_setcpu'],STOP,1000000,2000));assert c.reg(18)==STOP and c.reg(11)==0x7654
                    rejected=custom>1 or pace>4
                    if rejected:assert c.read(c.reg(8),4)==struct.pack('>I',9)
                    else:
                        assert c.reg(8)==STACK+4
                        assert int.from_bytes(c.read(BASE+0x1de4,4),'big')==(3 if custom==0 and pace==0 else custom)
                        assert int.from_bytes(c.read(BASE+0x1e04,4),'big')==max(0,pace-1)
                        request=struct.unpack('>II',c.read(0x30000,8))
                        assert request==((0,0) if custom==0 and pace==0 else (0x32a,0x7f3f)),request
                        if custom==0 and pace==0:assert int.from_bytes(c.read(BASE+sy['render_selected'],2),'big')==(30 if policy&256 and model==2 else 0)
                    options.append(dict(model=model,mode=custom,pace=pace,policy=policy,rejected=rejected));c.close()
    rng=random.Random(12);pictures=0
    for model in (2,4):
        c=CPU(blob,model);c.write(BASE+0x17b8,bytes.fromhex('4e75'));c.selected=sy['render_selected']
        c.allowed_stores=[(BASE+sy['flight_destinations'],BASE+sy['flight_destinations']+8)]
        for height in (128,166,200):
            for src in (bytes(320*height),bytes([255])*(320*height),rng.randbytes(320*height)):
                for internal in (0,1,3):
                    got,_=c.run(0x178a,src,height,internal,model);assert got==reference(src);pictures+=1
        c.close()
    pacing=[]
    for model in (2,4):
        # Exercise actual converter dispatch with a counted TOD wait stub.
        # New histories force full output, then flight_render_check covers reuse.
        for internal,pace in ((3,0),(0,0),(0,1),(0,2),(0,3),(1,0),(1,1),(1,2),(1,3)):
            for active,intro in ((0,0),(1,0),(0,1)):
                for height,history in ((128,0),(166,0),(200,0),(200,0xffffffff),(200,0xa0000)):
                    c=CPU(blob,model);c.selected=sy['render_selected']
                    c.write(BASE+0x17b8,bytes.fromhex('52b9000320004e75'))
                    c.write(BASE+sy['timing_active'],struct.pack('>H',active))
                    c.write(BASE+sy['intro_active'],struct.pack('>H',intro))
                    c.write(BASE+sy['flight_history'],struct.pack('>I',history))
                    c.allowed_stores=[(0x32000,0x32004),(0xa0000,0xa0000+128000)]
                    c.allowed_stores += [(BASE+sy[n],BASE+sy[n]+size) for n,size in (('flight_destinations',8),('flight_history_order',2))]
                    src=bytes(range(256))*(320*height//256+1);src=src[:320*height]
                    got,_=c.run(0x178a,src,height,internal,model,custom5=pace)
                    assert got==reference(src)
                    waits=int.from_bytes(c.read(0x32000,4),'big')
                    expected=int(not (active or intro)) if internal==3 else int(pace!=1)
                    assert waits==expected,(internal,pace,active,height,history,waits)
                    pacing.append(dict(model=model,internal=internal,pace=pace,active=active,intro=intro,height=height,history=history,waits=waits))
                    c.close()
    negatives=[]
    if a.negative_controls:
        for name in ('mode-map','nonflight-unlimited','flight-limited'):
            result=subprocess.run([sys.executable,__file__,str(a.build),'--output',str(out.with_name(out.stem+'-'+name+'.json')),'--sabotage',name],capture_output=True,text=True)
            assert result.returncode!=0 and 'AssertionError' in result.stderr,(name,result.stdout,result.stderr)
            negatives.append(name)
    out.write_text(json.dumps(dict(option_cases=len(options),pictures=pictures,options=options,pacing=pacing,negative_controls=negatives,release_sha256=meta['sha256'],diagnostics_absent=True),indent=2)+'\n')
    print(f'PASS: {len(options)} release option/cache cases and {pictures} complete converter outputs; {len(pacing)} pacing/output cases')
if __name__=='__main__':main()
