#!/usr/bin/env python3
"""Record ordinary runtime states at live ticks200/400/600 for replay checks."""
from runtime_lifecycle_probe import cap,command,key,m,a,base,s,irq,snapshot
from profile_window import ROOT
before=snapshot('record-request');assert before['mode']==0 and before['active_rate']==50 and before['consumer']<200
key(0x4c,1);lines=['delete','set $hit=0',f"break *{m['game_base']+0xe5f8:#x}",f"condition $bpnum *(unsigned char *){a+0x45:#x}==0",'commands','silent']
for tick in (200,400,600):
    lines += [f'if *(unsigned short *){a-0x940:#x}=={tick}',f'dump binary memory {(cap/("live-"+str(tick)+".bin")).relative_to(ROOT)} 0x200000 0x600000',f'printf "SAVED {tick}\\n"','end']
lines += [f'if *(unsigned short *){a-0x940:#x}==650','set $hit=1','else','continue','end','end',f'break *{irq:#x}',f"condition $bpnum *(unsigned int *){base+s['sim_clock_fields']:#x}>={before['sim_clock_fields']+1500}",'continue','printf "RECORD_HIT %u\\n", $hit','delete','monitor key 4c 0']
f=cap/'record.gdb';f.write_text('\n'.join(lines)+'\n');out=command('gdb source '+str(f.relative_to(ROOT)));(cap/'record-log.txt').write_text(out);assert 'RECORD_HIT 1' in out,out[-500:]
for tick in (200,400,600):assert f'SAVED {tick}' in out
snapshot('record-end')
