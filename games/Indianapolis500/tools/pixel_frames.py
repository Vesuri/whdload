#!/usr/bin/env python3
"""Read VERIFY pixel twins and validate the boot-selected demo fixture."""
import argparse,json,re,shutil,tempfile,os,struct
from pathlib import Path
from state_fields import command
from i500_report import regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('frames',type=int);p.add_argument('out',type=Path)
p.add_argument('dump',type=Path);p.add_argument('base',type=lambda x:int(x,0));a=p.parse_args()
blob=a.dump.read_bytes();found=regions(blob,a.base)
rr={name:lo for lo,hi,name,o in found}
assert 'slave' in rr,'live VERIFY slave not found'
lo=rr['slave'];magic=blob.find(b'I5PV',lo-a.base,lo-a.base+10000)
assert magic>=0,'VERIFY counters missing'
stats=a.base+magic
register_magic=blob.find(b'I5RG',lo-a.base,lo-a.base+10000)
assert register_magic>=0,'register-twin counters missing'
register_counter=a.base+register_magic+4
read=f'printf "I500PIX %u %u %u %u %u %u\\n", *(unsigned int *){stats+4:#x}, *(unsigned int *){stats+8:#x}, *(unsigned int *){stats+12:#x}, *(unsigned int *){stats+16:#x}, *(unsigned int *){stats+20:#x}, *(unsigned int *){register_counter:#x}'
a.out.mkdir(parents=True,exist_ok=True)
def parse(reply):
    values=re.findall(r'^I500PIX (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$',reply,re.M)
    assert values,reply[-1000:]
    return tuple(map(int,values[-1]))
values=parse(command(read))
views=os.environ.get('PIXEL_VIEWS','single').split()
control_offset=struct.unpack_from('>H',blob,magic+28)[0]
selector=stats+control_offset
hi=next(hi for lo_,hi,name,o in found if name=='slave')
assert stats <= selector and selector+4 <= hi, 'fixture selector outside slave'
assert len(views)==1, 'select one view per boot with WHD_ARGS CUSTOM3=0..6; debugger writes are unsupported'
fixture=struct.unpack_from('>I',blob,selector-a.base)[0]
assert 0<=fixture<=6,'invalid boot-time fixture'
if views!=['single']:
    assert fixture==(0 if views[0]=='opening' else int(views[0])), 'boot-time fixture differs from requested view'
fixture_read=f'printf "I500FIX %u %u %u\\n", *(unsigned int *){selector:#x}, *(unsigned short *){stats+24:#x}, *(unsigned short *){rr["game"]+0x268d0:#x}'
driving=os.environ.get('PIXEL_DRIVING')
driving_read='' if driving is None else f'printf "I500DRIVE %u %u %u\\n", *(unsigned char *){rr["game"]+0x268da:#x}, *(unsigned char *){rr["game"]+0x9b2e:#x}, *(unsigned short *){rr["game"]+0x7d4:#x}'
results=[];fixture_checks=[];driving_checks=[]
with (a.out/'pixels-gdb.txt').open('w') as log:
  for view in views:
    view=f'driving-{driving}' if driving is not None else ('natural-demo' if fixture==0 else str(fixture))
    start=values[0];target=start+a.frames
    while values[0]<target and not (any(values[2:4]) or values[5]):
        batch=min(target,values[0]+10)
        reply=command(f'''break *{rr['game']+0xb57e:#x}
while *(unsigned int *){stats+4:#x} < {batch} && *(unsigned int *){stats+12:#x} == 0 && *(unsigned int *){stats+16:#x} == 0 && *(unsigned int *){register_counter:#x} == 0
continue
end
delete
{read}
{fixture_read}
{driving_read}
''')
        log.write(reply+'\n');log.flush();values=parse(reply)
        observed=re.findall(r'^I500FIX (\d+) (\d+) (\d+)$',reply,re.M)
        assert observed, reply[-1000:]
        if driving is not None:
            dr=re.findall(r'^I500DRIVE (\d+) (\d+) (\d+)$',reply,re.M)
            assert dr,reply[-1000:]
            mode,flags,event=map(int,dr[-1]);assert mode==0 and not flags&2 and event==int(driving),'pixel run left requested cockpit event'
            driving_checks.append(dict(frames=values[0],mode=mode,flags=flags,event=event))
        selected,active,director=map(int,observed[-1])
        fixture_checks.append(dict(frames=values[0],selector=selected,active=active,director=director))
        assert selected==fixture, 'boot fixture changed'
        if fixture and values[0]>start:
            assert active==1 and director==50+150*(fixture-1), f'fixture inactive or wrong director: {observed[-1]}'
        print(f'pixel twins: {values[0]}/{target} frames, {values[1]} polygons, {values[2]} differences, {values[3]} guard failures, {values[5]} register failures',flush=True)
    results.append(dict(view=view,start=start,frames=values[0]-start,polygons=values[1],failures=values[2],guard_failures=values[3],register_failures=values[5]))
    (a.out/'pixels.json').write_text(json.dumps(dict(results=results,frames=values[0],polygons=values[1],failures=values[2],guard_failures=values[3],register_failures=values[5],first_difference=hex(values[4]),requested=a.frames,boot_fixture=fixture,fixture_tick=None if fixture==0 else 50+150*(fixture-1),fixture_checks=fixture_checks,driving_checks=driving_checks),indent=2)+'\n')
    if any(values[2:4]) or values[5]:
        with tempfile.TemporaryDirectory(prefix='i500-pixel-fail-') as temp:
            chip=Path(temp)/'chip.bin'
            command(f'dump binary memory {chip} 0 0x90000')
            shutil.move(str(chip),a.out/'failed-chip.bin')
            fast=Path(temp)/'fast.bin'
            command(f'dump binary memory {fast} {a.base:#x} {a.base+len(blob):#x}')
            shutil.move(str(fast),a.out/'failed-fast.bin')
        raise RuntimeError('pixel-twin or guard mismatch; retained local chip image')
print('requested pixel-twin run passed',flush=True)
