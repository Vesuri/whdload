#!/usr/bin/env python3
"""Single native-pitch-word diagnostic, verified before any resumed instruction."""
import json,struct,sys,re,subprocess
from pathlib import Path
from profile_window import ROOT,command
from simulation_fixture import read_fixture,compare
cap=Path(sys.argv[1]);m=json.loads((cap/'anchor.json').read_text())
assert m['active_simulation_word']==20 and m['simulation_tick']==220
mem=(cap/'memory.bin').read_bytes();addr=m['data_base']+0x7ffe-0x92e+0x1a
off=addr-m['memory_base'];before=struct.unpack_from('>h',mem,off)[0];assert before==67
reference={t:s for t,hz,s in read_fixture(ROOT/'tmp/prof/natural-crest20','bridge-end.bin')}
initial=read_fixture(cap);assert all(s==reference[t] for t,hz,s in initial)
script=cap/'pitch-write.gdb'
script.write_text(f'set *(short *){addr:#x}={before+1}\nmaintenance flush register-cache\nprintf "APPLIED %d\\n", *(short *){addr:#x}\n')
try:
    result=command('gdb source '+str(script.resolve()))
    (cap/'pitch-write.txt').write_text(result);assert re.findall(r'^APPLIED (.*)$',result,re.M)==['68']
    command(f'gdb dump binary memory {cap}/after-write.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
    after=(cap/'after-write.bin').read_bytes();expected=bytearray(mem);struct.pack_into('>h',expected,off,68)
    assert after==expected,'Unexpected RAM changes before resume'
    (cap/'intervention.json').write_text(json.dumps(dict(address=addr,original=before,new=68,changed_bytes=[i for i,(a,b) in enumerate(zip(mem,after)) if a!=b],whole_ram_verified=True,initial_exact_full_states=len(initial),scope='One-time body pitch +1 before resumed native physics. Cached wheel coordinates unchanged deliberately; not a runtime rule or coherent alternative course initialization.'),indent=2)+'\n')
    subprocess.run([sys.executable,'tools/release_step_probe.py',str(cap),'11.7'],check=True)
    command(f'gdb dump binary memory {cap}/release-end.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
finally:
    subprocess.run([sys.executable,'tools/driving.py','quit'],check=False)
