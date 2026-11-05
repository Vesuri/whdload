#!/usr/bin/env python3
"""Controlled full-queue fault injection; not a natural-overload measurement."""
import json,re,struct,sys
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]).resolve();m=json.loads((cap/'anchor.json').read_text())
symbols={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
addr=lambda n:m['slave_base']+symbols[n]
rd=lambda b,n,fmt='H':struct.unpack_from('>'+fmt,b,addr(n)-m['memory_base'])[0]
def snapshot(name):
 p=cap/name
 command(f'gdb dump binary memory {p.relative_to(ROOT)} 0x200000 0x600000')
 return p.read_bytes()
command('stop')
# Stop before the field producer, after the interrupt has saved its scratch regs.
command(f'gdb delete\ntbreak *{addr("sim_clock_interrupt")+6:#x}\ncontinue')
before=snapshot('overflow-before.bin')
assert rd(before,'sim_schedule_active')==1 and rd(before,'sim_schedule_rate')==50
assert rd(before,'sim_schedule_overflow')==0
# Model a full ring across the 16-bit sequence wrap; change no payload/flags.
command(f'gdb set {{unsigned short}}{addr("sim_schedule_read"):#x} = 65534\nset {{unsigned short}}{addr("sim_schedule_write"):#x} = 254')
seed=snapshot('overflow-seeded.bin')
assert rd(seed,'sim_schedule_read')==65534 and rd(seed,'sim_schedule_write')==254
allowed={addr(n)-m['memory_base']+i for n in ('sim_schedule_read','sim_schedule_write') for i in range(2)}
assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(before,seed)))
exit_address=addr('sim_schedule_overflow_exit')
log=command(f'gdb delete\ntbreak *{exit_address:#x}\ncontinue')
entered=snapshot('overflow-entered.bin')
assert rd(entered,'sim_schedule_overflow')==1 and rd(entered,'perf_failure','I')==12
assert rd(entered,'sim_schedule_ticks','I')==rd(seed,'sim_schedule_ticks','I')
assert rd(entered,'sim_schedule_read')==65534 and rd(entered,'sim_schedule_write')==254
q=addr('sim_schedule_queue')-m['memory_base']
assert entered[q:q+2048]==seed[q:q+2048]
# Stop at the actual WHDLoad dispatch after cleanup and argument setup.
abort_address=exit_address+18
assert entered[abort_address-m['memory_base']:abort_address-m['memory_base']+4]==bytes.fromhex('4ee80004')
log+=command(f'gdb delete\ntbreak *{abort_address:#x}\ncontinue\ndump binary memory {(cap/"overflow-abort-stack.bin").relative_to(ROOT)} $sp $sp+8')
final=snapshot('overflow-cleaned.bin')
reason,message=struct.unpack('>II',(cap/'overflow-abort-stack.bin').read_bytes())
assert reason==43 and message==addr('sim_schedule_overflow_message')
assert rd(final,'sim_clock_installed')==rd(final,'sim_schedule_active')==0
assert rd(final,'sim_schedule_a4','I')==0
assert rd(final,'sim_clock_removes','I')==rd(seed,'sim_clock_removes','I')+1
assert final[q:q+2048]==seed[q:q+2048]
at=message-m['memory_base'];message_text=final[at:final.index(0,at)].decode()
(cap/'overflow-log.txt').write_text(log)
report=dict(injected_read=65534,injected_write=254,queued=256,queue_bytes_preserved=2048,
 published_after_full=0,overflow=1,failure=12,clock_removed=True,
 whdload_reason=reason,message=message_text,
 scope='Controlled cursor-only fault injection into active runtime at field-producer entry. Live producer detects full wrapped ring without writing payload or publishing input; main-task error path removes clock and prepares WHDLoad FAILMSG. Dispatch execution checked separately.')
(cap/'overflow-exit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
