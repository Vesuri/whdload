#!/usr/bin/env python3
"""Summarize native execution and input-only gameplay coverage, without FPS claims."""
import argparse
import json
from pathlib import Path
import re
import struct
from perf_status import status

STATE_NAMES = ('practice', 'session_counter', 'segment', 'damage', 'speed', 'fuel', 'full_view',
               'inset', 'effect_pending', 'effect_active', 'animation', 'race_end',
               'rescue', 'map')
EVENTS = {0xc7f0:'view_toggle', 0xc736:'map_toggle', 0xc7d2:'rescue_accepted',
          0x103a2:'pit_return', 0xbf32:'session_end', 0xd3d6:'opponent_update',
          0xc75c:'lap_times', 0xc6b8:'positions', 0xc6fe:'lead_time',
          0xbe12:'pause', 0xbe40:'pause_key_check', 0x13cde:'pit_key',
          0xfb84:'wall_contact', 0xfc9e:'track_collision', 0x112f4:'effect_draw',
          0x14764:'pit_departure', 0x120ca:'race_selection',
          0xe1a2:'weather_warning', 0xe1f8:'weather_start'}

def fixture(path):
    data=path.read_bytes()
    positions=[m.start() for m in re.finditer(b'PDCOV00[12]',data)]
    active=[pos for pos in positions if struct.unpack_from('>H',data,pos+8)[0] or (data[pos+7:pos+8]==b'2' and struct.unpack_from('>I',data,pos+32)[0])]
    assert len(active)==1, f'Expected one initialized coverage block, got {len(active)}'
    pos=active[0]
    version=data[pos+7:pos+8]
    assert version in (b'1',b'2')
    result=dict(zip(('started','done','epoch','tape_bytes','keys','simulation_calls','shift','buttons'),
                    struct.unpack_from('>HHIIIIHH',data,pos+8)))
    if version==b'2':
        result.update(zip(('native_scenes','native_full','native_inset','native_effect','native_animation'),
                          struct.unpack_from('>5I',data,pos+32)))
    return result

def opponents(path, game):
    data=path.read_bytes()
    count=struct.unpack_from('>h',data,game+0xa6e+0x340)[0]+1
    pointer=struct.unpack_from('>I',data,game+0xa6e+0x342)[0]
    assert 0<=count<=16 and pointer+count*190<=len(data)
    return [dict(zip(('id','segment','x','y','z'),
                     [struct.unpack_from('>h',data,pointer+slot*190+offset)[0]
                      for offset in (0,2,0x10,0x12,0x14)])) for slot in range(count)]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture',type=Path)
    p.add_argument('--require-long',action='store_true',help='Require views, opponents, collisions, rescue, departure and restart')
    p.add_argument('--require-effects',action='store_true',help='Require natural effects and native fallback evidence')
    a=p.parse_args()
    log=(a.capture/'swaps-gdb.txt').read_text()
    events={}
    for field,offset in re.findall(r'^PDEVENT (-?\d+) (0x[0-9a-f]+)$',log,re.M):
        name=EVENTS.get(int(offset,16),offset)
        item=events.setdefault(name,dict(count=0,first_field=int(field),last_field=int(field)))
        item['count']+=1;item['last_field']=int(field)
    rows=[list(map(int,line.split())) for line in re.findall(r'^PDSTATE (.+)$',log,re.M)]
    assert all(len(row)==len(STATE_NAMES)+1 for row in rows)
    states={name:dict(min=min(vals),max=max(vals),nonzero=sum(v!=0 for v in vals),
                      distinct=len(set(vals)))
            for i,name in enumerate(STATE_NAMES,1) if (vals:=[row[i] for row in rows])}
    before=status(a.capture/'code.bin');after=status(a.capture/'final-code.bin')
    failures={key:after.get(key,0) for key in ('pixel_failures','guard_failures','scratch_failures','register_failures')}
    opponent_states={name:opponents(a.capture/file,before['game']) for name,file in (('initial','chip.bin'),('final','final-chip.bin'))}
    tracks={name:struct.unpack_from('>H',(a.capture/file).read_bytes(),before['game']+0xa6e+0x118)[0] for name,file in (('initial','chip.bin'),('final','final-chip.bin'))}
    result=dict(tracks=tracks,opponents=opponent_states,configuration=json.loads((a.capture/'configuration.json').read_text()),
                fixture_initial=fixture(a.capture/'code.bin'),fixture_final=fixture(a.capture/'final-code.bin'),
                presentations=len(rows),events=events,states=states,
                completed_staged_scenes=after['staged_frames']-before['staged_frames'],failures=failures)
    print(json.dumps(result,indent=2))
    assert not any(failures.values()), 'Renderer verification failure'
    if a.require_long:
        assert opponent_states['initial'] and opponent_states['initial']!=opponent_states['final'], 'No changed opponent positions'
        assert result['fixture_final']['done'], 'Input tape did not finish'
        assert result['completed_staged_scenes']>0, 'No staged scenes validated'
        for name in ('view_toggle','map_toggle','opponent_update','lap_times','positions',
                     'lead_time','pause','rescue_accepted','pit_return','pit_departure',
                     'session_end','race_selection'):
            assert events.get(name,{}).get('count',0)>0, f'Missing native event: {name}'
        assert events.get('wall_contact',{}).get('count',0)+events.get('track_collision',{}).get('count',0)>0, 'No collision evidence'
        assert states['full_view']['nonzero'] and states['map']['nonzero'], 'Missing resulting view state'
        assert result['fixture_final']['native_full']>0, 'No full-view fallback observed'
        assert events['race_selection']['last_field']>events['session_end']['first_field'], 'No restart after session end'
        assert events['pit_return']['first_field']>events['rescue_accepted']['first_field'], 'No pit return after rescue'
        assert events['pit_departure']['last_field']>events['pit_return']['first_field'], 'No pit departure after rescue'
    if a.require_effects:
        assert events.get('effect_draw',{}).get('count',0)>0, 'No natural effect rendering observed'
        assert result['fixture_final']['native_effect']>0, 'No effect fallback observed'


if __name__=='__main__':main()
