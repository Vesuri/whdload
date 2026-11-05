#!/usr/bin/env python3
"""Observe native contact for ten ticks of a source-seeded inverted start.
Run on a paused quick_start tick0 capture. Requires SIM_FIXTURE_INVERTED; debugger memory writes are unsupported.
It does not provide natural-driving handling acceptance.
"""
import json,re,sys,struct
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]).resolve(); meta=json.loads((cap/'anchor.json').read_text())
assert meta['simulation_tick']==0 and meta['opponent']==0
assert not (cap/'inverted-log.txt').exists()
g=meta['game_base']; a4=meta['data_base']+0x7ffe
script=f"""gdb delete
set $car={a4-0x92e:#x}
tbreak *{g+0xc61a:#x}
commands
silent
printf "MATRIX "
x/9hd $a4+0xbae
printf "WHEELS "
x/12hd $car+0x74
continue
end
break *{g+0xcb1c:#x}
commands
silent
set $p=*(unsigned int *)($a5-0xe6)
printf "BEFORE %u %u %d %d %d %d %d %d %d\\n", *(unsigned short *)($a4-0x940), *(unsigned char *)($a5-3), *(short *)($a4+0xbc0), *(int *)$p, *(int *)($p+4), *(int *)($p+8), *(short *)($a5-0x6a), *(short *)($a5-0x68), *(short *)($a5-0x66)
continue
end
break *{g+0xcb44:#x}
commands
silent
printf "AFTER %u %u %d %d %d\\n", *(unsigned short *)($a4-0x940), *(unsigned char *)($a5-3), *(int *)$p, *(int *)($p+4), *(int *)($p+8)
continue
end
break *{g+0xcb48:#x}
commands
silent
printf "FALL %u %u %d %d %u\\n", *(unsigned short *)($a4-0x940), *(unsigned char *)($a5-3), *(short *)($a4+0xbc0), *(short *)($a5-8), *(unsigned char *)($car+0xc1)
continue
end
break *{g+0x114f6:#x}
commands
silent
printf "CRASH %u %u %u %u\\n", *(unsigned short *)($a4-0x940), *(unsigned int *)$sp-{g}, *(unsigned short *)($sp+4), *(unsigned short *)($sp+6)
continue
end
break *{g+0xe7b4:#x}
commands
silent
printf "STEP %u %d %d %d %d %d %d %u %u\\n", *(unsigned short *)($a4-0x940), *(int *)$car, *(int *)($car+4), *(int *)($car+8), *(short *)($car+0x18), *(short *)($car+0x1a), *(short *)($car+0x1c), *(unsigned char *)($car+0xc1), *(unsigned short *)($car+0x2c)
if *(unsigned short *)($a4-0x940)<10
continue
end
end
continue
info registers pc
"""
(cap/'inverted-probe.gdb').write_text(script)
answer=command(script);(cap/'inverted-log.txt').write_text(answer)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',answer,re.M)[1],16)==g+0xe7b4
command(f'gdb dump binary memory {cap.relative_to(ROOT)}/inverted-end.bin 0x200000 0x600000')
endmem=(cap/'inverted-end.bin').read_bytes()
mark=endmem.index(b'4DINVERT')
assert struct.unpack_from('>HHI',endmem,mark+8)==(1,4,1)
assert struct.unpack_from('>h',endmem,meta['data_base']+0x7ffe-0x912-meta['memory_base'])[0] != 0
before=[[int(v) for v in line.split()[1:]] for line in answer.splitlines() if line.startswith('BEFORE ')]
after=[[int(v) for v in line.split()[1:]] for line in answer.splitlines() if line.startswith('AFTER ')]
falls=[[int(v) for v in line.split()[1:]] for line in answer.splitlines() if line.startswith('FALL ')]
crashes=[[int(v) for v in line.split()[1:]] for line in answer.splitlines() if line.startswith('CRASH ')]
steps=[[int(v) for v in line.split()[1:]] for line in answer.splitlines() if line.startswith('STEP ')]
assert len(before)==len(after) and len(steps)==10
assert before, "No inverted correction coverage"
for b,a in zip(before,after):
 assert b[:2]==a[:2]
 assert [a[n+2]-b[n+3] for n in range(3)]==b[6:9]
result={'rate':meta['active_simulation_word'],'correction_calls':len(before),'before':before,'after':after,'crashes':crashes,'falls':falls,'steps':steps,'scope':'synthetic inverted pose with cached wheels rebuilt from native pre-displacement wheel positions; ten updates, not natural handling'}
(cap/'inverted-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'rate':result['rate'],'correction_calls':len(before),'steps':steps},indent=2))
