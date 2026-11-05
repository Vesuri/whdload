#!/usr/bin/env python3
"""Check the seeded, unshortened logical weather-cycle fixture.

Requires complete warning/onset/expiry/fades. Does not certify message pixels,
physical scanout, native cadence acceptance, or clock-domain lifecycle transfers.
"""
import argparse
from pathlib import Path
import re
import struct
from report_weather import advance_seed
from weather_cycle_state import locate, parse_values, snapshot
from weather_state import parse_values as native_values
from weather_fade_state import parse_values as fade_values, snapshot as fade_snapshot


def check(root):
    chip=(root/'final-chip.bin').read_bytes()
    code=(root/'final-code.bin').read_bytes()
    game=int((root/'game-base.txt').read_text(),0)
    base=int((root/'dump-base.txt').read_text(),0)
    record=locate(chip,code,game,base)
    assert record is not None
    tag=code.find(b'PDWCTS01',record-base+72,record-base+4096)
    assert tag>=0
    activations,step,fixture_clock=struct.unpack_from('>3I',code,tag+8)
    assert activations==1 and step>=200
    initial=snapshot(root)
    final=snapshot(root,True)
    assert initial['forecasts']==initial['starts']==initial['expiries']==0
    assert (final['forecasts'],final['starts'],final['expiries'])==(1,1,1)
    assert final['active']==final['message']==final['palette']==0 and final['owned']==1
    assert (final['messages'],final['palettes'])==(1,1)
    assert final['forecast_clock']==fixture_clock
    assert final['forecast_deadline']==final['active_deadline']==0xffffffff
    assert final['forecast_flag']==1 and final['effects']==0
    text=(root/'swaps-gdb.txt').read_text()
    cycles=[(int(f),int(off,16),parse_values(v)) for f,off,v in re.findall(
        r'^PDWCYCLE_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',text,re.M)]
    natives=[(int(f),int(off,16),native_values(v)) for f,off,v in re.findall(
        r'^PDWEATHER_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',text,re.M)]
    def one(events,offset):
        rows=[s for _,off,s in events if off==offset]
        assert len(rows)==1, f'Missing/duplicate native boundary {offset:#x}'
        return rows[0]
    warning=one(natives,0xe1ca)
    published=one(natives,0xe1d4)
    queued=one(cycles,0xe1f6)
    before=one(natives,0xe1f8)
    calculated=one(natives,0xe23c)
    started=one(natives,0xe25c)
    assert warning['rng']==1 and warning['d7']==fixture_clock
    deadline=fixture_clock+5000
    assert published['forecast_deadline']==deadline
    assert queued['active']==1 and queued['message']==1 and queued['message_ptr']!=0
    assert queued['clock']==fixture_clock and queued['forecast_deadline']==deadline
    onset=final['start_clock']
    assert one(cycles,0xe1f8)['clock']==onset
    assert before['forecast_deadline']==deadline and 0<=onset-deadline<20
    track=before['track']
    native_base=5*struct.unpack_from('>h',chip,game+0x2c1a+2*track)[0]
    seed=advance_seed(before['rng'],1)
    limit=(native_base>>2)&65535
    if limit>=32768:limit-=65536
    duration=(native_base+4*((((seed&32767)*limit*2)&0xffffffff)>>16))&0xffffffff
    assert calculated['rng']==seed and calculated['d0']==duration
    assert calculated['d1']==native_base
    assert final['duration']==duration and final['seed_before']==before['rng'] and final['seed_after']==seed
    assert started['active_deadline']==onset+duration
    assert started['forecast_deadline']==0xffffffff and started['transition']==15
    assert started['steering_x']==started['steering_y']==0
    assert started['effects_enabled']==(65535 if chip[game+0x2076+track] else 0)
    expiry=final['expiry_clock']
    assert 0<=expiry-(onset+duration)<148, 'Expiry escaped eight-control polling bound'
    expired=next(s for _,off,s in cycles if off==0xccee and s['expiries']==1)
    assert expired['transition']==65521 and expired['effects']==0
    assert expired['forecast_deadline']==expired['active_deadline']==0xffffffff
    fades=[(int(f),int(off,16),fade_values(v)) for f,off,v in re.findall(
        r'^PDWFADE_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',text,re.M)]
    last_fade=fade_snapshot(root,True)
    assert (last_fade['positive'],last_fade['negative'],last_fade['gears'])==(15,15,2)
    assert last_fade['expected']==last_fade['active']==last_fade['pending']==last_fade['transition']==0
    rows=[]
    for direction,start,delay,period in (('positive',onset,192,280),('negative',expiry,236,232)):
        for n in range(1,16):
            samples=[s for _,off,s in fades if off==0xccee and s[direction]==n and s['start']==start]
            assert samples, f'Missing {direction} fade step {n}'
            s=samples[0]
            assert s['last']==start+delay+(n-1)*period
            expected=(15-n if direction=='positive' else n-15)&65535
            assert s['transition']==s['expected']==expected
            rows.append((direction,n,s['last']-start,expected))
    print(f'{root.name}: one warning, onset and expiry; unchanged native duration arithmetic; all 30 fade steps complete')
    print(f'  Warning delay={(onset-fixture_clock)*5} ms; selected active duration={duration*5} ms; expiry lateness={(expiry-onset-duration)*5} ms')
    print(f'  One deferred message and expiry palette delivered; no pending cycle/fade work')
    return (onset-fixture_clock,duration,expiry-onset,before['rng'],seed,rows)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures',type=Path,nargs='+')
    results=[check(root) for root in p.parse_args().captures]
    assert all(result==results[0] for result in results), 'Logical weather histories differ'
    print('All supplied logical cycle histories match; lifecycle and presentation acceptance remain separate.')
