#!/usr/bin/env python3
"""Native sparse forward seek with exact reconstruction captures."""
from runtime_lifecycle_probe import cap,command,key,m,a,base,s,irq,snapshot
from profile_window import ROOT
b=snapshot('seek-request');assert b['mode']==2 and b['consumer']==0 and b['replay_selection']==0
key(0x44,1)
# Hold native Return while the toolbar previews a destination, then release.
out=command(f'gdb delete\nbreak *{irq:#x}\ncondition $bpnum *(unsigned int *){base+s["sim_clock_fields"]:#x}>={b["sim_clock_fields"]+300}\ncontinue\ndelete')
(cap/'seek-hold.log').write_text(out);key(0x44,0);b=snapshot('seek-release')
lines=['delete','set $failed=0','set $done=0',f"break *{base+s['sim_history_failed']:#x}",'commands','silent','set $failed=1','end',f"break *{m['game_base']+0xe518:#x}",'commands','silent','printf "TARGET %u\\n", *(unsigned short *)($sp+4)','continue','end',f"break *{m['game_base']+0xe5e0:#x}",'commands','silent',f'printf "RESTORED %u\\n", *(unsigned short *){a-0x940:#x}','continue','end',f"break *{m['game_base']+0xe5f8:#x}",'commands','silent']
for t in (1500,1550,1600):
 lines += [f'if *(unsigned short *){a-0x940:#x}=={t}',f'dump binary memory {(cap/("seek-"+str(t)+".bin")).relative_to(ROOT)} 0x200000 0x600000',f'printf "SAVED {t}\\n"','end']
lines += ['continue','end',f"break *{m['game_base']+0xa25a:#x}",'commands','silent','set $done=1','end',f'break *{irq:#x}',f"condition $bpnum *(unsigned int *){base+s['sim_clock_fields']:#x}>={b['sim_clock_fields']+1000}",'continue','printf "HISTORY_FAILURE %u DONE %u\\n", $failed, $done','info registers pc','delete']
p=cap/'seek.gdb';p.write_text('\n'.join(lines)+'\n');out=command('gdb source '+str(p.relative_to(ROOT)));(cap/'seek.log').write_text(out);print(out[-1000:]);assert 'HISTORY_FAILURE 0 DONE 1' in out;snapshot('seek-result')
