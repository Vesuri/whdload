import json,re,struct,sys
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]);m=json.loads((cap/'anchor.json').read_text())
s={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
names=['sim_workspace_base','sim_schedule_queue','sim_history_inputs','sim_history_records','sim_replay_pending_file','sim_replay_save_readback']
r=command('gdb '+'\n'.join(f'p /u *(unsigned int *){m["slave_base"]+s[n]:#x}' for n in names));values=[int(x) for x in re.findall(r'^\$\d+ = (\d+)',r,re.M)];assert len(values)==len(names),r
ptr=dict(zip(names,values));b=ptr['sim_workspace_base'];assert b and b%4==0
sizes=[2048,30000,7840,63916,63916];at=b
for n,size in zip(names[1:],sizes):assert ptr[n]==at,(n,ptr[n],at);at+=size
f=cap/'workspace.bin';command(f'gdb dump binary memory {f.relative_to(ROOT)} {b:#x} {b+167936:#x}');data=f.read_bytes();assert not any(data[167720:]),'Workspace tail overwritten'
w=json.loads((cap/'window.json').read_text());assert w['end']['sim_schedule_overflow']==0
assert w['consumed_steps']>0
(cap/'workspace-check.json').write_text(json.dumps(dict(pointers=ptr,used_bytes=167720,reserved_bytes=167936,tail_clear=True,consumed_steps=w['consumed_steps']),indent=2)+'\n')
print('Runtime workspace pointers, bounds and queue: passed')
