#!/usr/bin/env python3
"""Observe native backward seek restoring a later disk-loaded checkpoint."""
from runtime_lifecycle_probe import cap,command,key,m,a,base,s,irq,snapshot
from profile_window import ROOT
before=snapshot('seek-request');assert before['mode']==2 and before['replay_selection']==1 and before['consumer']==1651
lines=['delete','set $hit=0',f"break *{m['game_base']+0xa268:#x}",'commands','silent','monitor key 44 0','continue','end',f"break *{m['game_base']+0xe5e0:#x}",'commands','silent',f'dump binary memory {(cap/"seek-restored.bin").relative_to(ROOT)} 0x200000 0x600000',f'printf "RESTORED %u\\n", *(unsigned short *){a-0x940:#x}','continue','end',f"break *{m['game_base']+0xe5f8:#x}",'commands','silent']
for t in (1550,1600):
 lines += [f'if *(unsigned short *){a-0x940:#x}=={t}',f'dump binary memory {(cap/("seek-"+str(t)+".bin")).relative_to(ROOT)} 0x200000 0x600000',f'printf "SAVED {t}\\n"','end']
lines += ['continue','end',f"break *{m['game_base']+0xa45a:#x}",'commands','silent','set $hit=1','end',f'break *{irq:#x}',f"condition $bpnum *(unsigned int *){base+s['sim_clock_fields']:#x}>={before['sim_clock_fields']+1000}",'monitor key 44 1','continue','printf "SEEK_HIT %u\\n", $hit','delete','monitor key 44 0']
p=cap/'seek.gdb';p.write_text('\n'.join(lines)+'\n');out=command('gdb source '+str(p.relative_to(ROOT)));(cap/'seek.log').write_text(out);assert 'SEEK_HIT 1' in out,out[-1000:];snapshot('seek-end')
