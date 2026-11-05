#!/usr/bin/env python3
"""Observe native sound publication/consumption over exactly 250 PAL fields.
No guest memory writes. Counts are GDB convenience variables, not guest state.
Run against an unmodified native sound producer/consumer in a live capture.
"""
import argparse, json, re, struct
from pathlib import Path
from profile_window import command, ROOT

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
a = p.parse_args()
cap = a.capture.resolve()
m = json.loads((cap/'anchor.json').read_text())
b = (cap/'memory.bin').read_bytes()
s = {n: int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9a-fA-F]+)\s*$', (cap/'slave.lst').read_text(encoding='latin1'), re.M)}
base = m['marker']+8-s['tape_game']
aa = m['data_base']+0x7ffe
game = m['game_base']
irq = base+s['sim_clock_interrupt']+10
clock = base+s['sim_clock_fields']
patched = 'sim_sound_pending' in s
checks = [(irq, '4cdf7ffe70004e75')]
if not patched: checks += [(game+0x10904, '196c00448c94'), (game+0x79b4, '426c0076')]
for addr, expected in checks:
    assert b[addr-m['memory_base']:addr-m['memory_base']+len(bytes.fromhex(expected))] == bytes.fromhex(expected)

def read_expr(addr, width=16):
    return f'*(unsigned {"int" if width==32 else "short"} *){addr:#x}'

def save(name):
    path = cap/name
    command(f'gdb dump binary memory {path.relative_to(ROOT)} 0x200000 0x600000')
    return path.read_bytes()

def state(mem):
    def val(addr, width=16):
        return struct.unpack_from('>I' if width==32 else '>H', mem, addr-m['memory_base'])[0]
    r = {k: val(addr,width) for k,addr,width in specs}
    r['queue'] = (r['write']-r['read'])%40
    return r

specs = [('field',clock,32),('raw_ticks',aa+0x2342,32),('write',aa+0x72,16),('read',aa+0x74,16),('elapsed',aa+0x76,16),('latch',aa-0x217c,16),('divider',aa-0xbe,16),('consumer',aa-0x940,16),('failure',base+s['perf_failure'],32)]
if patched:
    specs += [(key,base+s[sym],width) for key,sym,width in [('pending','sim_sound_pending',16),('offered','sim_sound_published',32),('taken','sim_sound_played',32),('selftests','sim_sound_passed',32)]]
res = command(f'gdb delete\ntbreak *{irq:#x}\ncontinue\ninfo registers pc')
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',res,re.M)[1],16)==irq
start = state(save('sound-start.bin'))
fields = ', '.join(read_expr(addr,width) for _,addr,width in specs)
fmt = 'SOUND '+' '.join(['%u']*(len(specs)+2))+r'\n'
script = f'''gdb delete
set $sound_written=0
set $sound_played=0
break *{game+0x10904:#x} if *(unsigned char *){aa+0x44:#x}==0
commands
silent
set $sound_written=$sound_written+1
continue
end
break *{game+0x79b4:#x}
commands
silent
set $sound_played=$sound_played+1
continue
end
break *{irq:#x}
commands
silent
printf "{fmt}", {fields}, $sound_written, $sound_played
if {read_expr(clock,32)} < {start['field']+250}
continue
end
end
continue
info registers pc'''
if patched:
    # Observe the real native sound function's incoming stack arguments.
    # At entry: return.L, record.L, elapsed.W. No guest writes.
    part = script.index(f'break *{irq:#x}')
    script = f'''gdb delete
set $sound_written=0
set $sound_played=0
break *{game+0x10940:#x}
commands
silent
set $sound_played=$sound_played+1
printf "RECORD %u %u\\n", *(unsigned int *)($sp+4), *(unsigned short *)($sp+8)
continue
end
'''+script[part:]
res = command(script)
(cap/'sound-field-log.txt').write_text(res)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',res,re.M)[1],16)==irq
names = [k for k,_,_ in specs]+['published','played']
rows = []
for match in re.finditer(r'^SOUND (.*)$',res,re.M):
    values = list(map(int,match[1].split()))
    assert len(values)==len(names)
    row = dict(zip(names,values))
    row['queue']=(row['write']-row['read'])%40
    rows.append(row)
assert [r['field'] for r in rows] == list(range(start['field']+1,start['field']+251))
end = state(save('sound-end.bin'))
assert end['field']==start['field']+250 and end['failure']==0
assert all(r['failure']==0 for r in rows)
last=rows[-1]
r = dict(fields=250, start=start, end=end, published=last['published'], played=last['played'], queue_growth=last['published']-last['played'], max_queue=max(x['queue'] for x in rows), timer_latches=sorted({x['latch'] for x in rows}), dividers=sorted({x['divider'] for x in rows}), raw_ticks=end['raw_ticks']-start['raw_ticks'], rows=rows)
r['queue_count_agrees'] = (start['queue']+r['queue_growth'])%40 == end['queue']
if patched:
    records = [tuple(map(int,x)) for x in re.findall(r'^RECORD (\d+) (\d+)$',res,re.M)]
    assert len(records)==last['played'] and records
    assert all(dt==2 and aa+0x536<=ptr<aa+0x536+40*34 and (ptr-aa-0x536)%34==0 for ptr,dt in records)
    assert all(0<=row['pending']<=40 and row['selftests']==42 for row in rows)
    r['published']=end['offered']-start['offered']
    r['played']=end['taken']-start['taken']
    r['queue_growth']=None  # mailbox coalescing has no FIFO queue
    r['queue_count_agrees']=None
    r['native_calls']=len(records)
    r['native_intervals']=sorted({dt for _,dt in records})
    r['record_indices']=[(ptr-aa-0x536)//34 for ptr,_ in records]
    r['selftests']=end['selftests']
else:
    assert r['queue_count_agrees'], r
(cap/'sound-window.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2))
command('gdb delete')
