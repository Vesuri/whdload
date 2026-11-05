#!/usr/bin/env python3
"""Native forward seek reproduction; stops before the fatal history handler."""
from runtime_lifecycle_probe import cap,command,key,m,a,base,s,irq,snapshot
from profile_window import ROOT
b=snapshot('seek-request');assert b['mode']==2 and b['consumer']==0 and b['replay_selection']==0
key(0x44,1)
# Hold native Return while the toolbar previews a destination, then release.
out=command(f'gdb delete\nbreak *{irq:#x}\ncondition $bpnum *(unsigned int *){base+s["sim_clock_fields"]:#x}>={b["sim_clock_fields"]+300}\ncontinue\ndelete')
(cap/'seek-hold.log').write_text(out);key(0x44,0);b=snapshot('seek-release')
lines=['delete','set $failed=0',f"break *{base+s['sim_history_failed']:#x}",'commands','silent','set $failed=1','end',f"break *{m['game_base']+0xe518:#x}",'commands','silent','printf "TARGET %u\\n", *(unsigned short *)($sp+4)','continue','end',f'break *{irq:#x}',f"condition $bpnum *(unsigned int *){base+s['sim_clock_fields']:#x}>={b['sim_clock_fields']+1000}",'continue','printf "HISTORY_FAILURE %u\\n", $failed','info registers pc','delete']
p=cap/'seek.gdb';p.write_text('\n'.join(lines)+'\n');out=command('gdb source '+str(p.relative_to(ROOT)));(cap/'seek.log').write_text(out);print(out[-1200:]);snapshot('seek-result')
