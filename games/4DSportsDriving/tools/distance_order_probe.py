#!/usr/bin/env python3
"""Observe drivetrain update and its subsequent distance step on the flat approach."""
import sys,json,re,struct
from pathlib import Path
from profile_window import command
ordered='--ordered-engine' in sys.argv
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());g=m['game_base'];hz=m['active_simulation_word'];end=round(float(sys.argv[2])*hz)
script=f'''gdb delete
break *{g+0xf60c:#x}
commands
silent
printf "ACCEL %d %d %d %d %d\\n", *(unsigned short *)($a4-0x940), *(unsigned short *)($a5-2), *(short *)($a5-4), *(unsigned short *)(*(unsigned int *)($a5+12)+0x2c), *(unsigned short *)(*(unsigned int *)($a5+12)+0x2e)
continue
end
break *{g+0xf61c:#x}
commands
silent
printf "SCALED %d %d\\n", *(unsigned short *)($a4-0x940), *(short *)($a5-4)
continue
end
break *{g+0xf66e:#x}
commands
silent
printf "APPLIED %d %d\\n", *(unsigned short *)($a4-0x940), *(unsigned short *)($a5-2)
continue
end
break *{g+0xc326:#x}
commands
silent
printf "DIST %d %d %d %d\\n", *(unsigned short *)($a4-0x940), *(unsigned short *)(*(unsigned int *)($a5+8)+0x2a), *(unsigned short *)(*(unsigned int *)($a5+8)+0x2c), *(unsigned short *)(*(unsigned int *)($a5+8)+0x2e)
continue
end
break *{g+0xc346:#x}
commands
silent
printf "STEP %d %d\\n", *(unsigned short *)($a4-0x940), *(unsigned short *)($a5-6)
continue
end
break *{g+0xe7b4:#x}
commands
silent
printf "END %d %d %d %d\\n", *(unsigned short *)($a4-0x940), *(int *)($a4-0x92e), *(int *)($a4-0x92a), *(int *)($a4-0x926)
if *(unsigned short *)($a4-0x940)<{end}
continue
end
end
continue
delete
'''
(p/'distance-order.gdb').write_text(script);out=command(script);(p/'distance-order.txt').write_text(out)
records={tag:[list(map(int,s.split())) for s in re.findall(r'^'+tag+r' (.*)$',out,re.M)] for tag in ('ACCEL','SCALED','APPLIED','DIST','STEP','END')}
assert all(len(v)==end-m['simulation_tick'] for v in records.values()),{k:len(v) for k,v in records.items()}
mem=(p/'memory.bin').read_bytes();private=mem.index(b'4DA4PHYS')+12;carry=struct.unpack_from('>H',mem,private+4)[0];rows=[]
for ac,sc,ap,di,st,en in zip(*records.values()):
 assert len({v[0] for v in (ac,sc,ap,di,st,en)})==1
 q=di[2]*1408//15360
 if hz==50:
  if ordered:
   eligible=ac[1]==ac[4] and di[2]==ap[1]
   delta=ap[1]-ac[1] if eligible else 0
   pred,carry=divmod(max(0,q*160+11*delta+carry),400)
  else:pred,carry=divmod(q*2+carry,5)
 else:assert hz==20;pred=q
 assert st[1]==pred,(st,pred)
 rows.append(dict(tick=ac[0],old_local_speed=ac[1],nominal_acceleration=ac[2],old_target=ac[3],saved_old_target=ac[4],scaled_acceleration=sc[1],applied_speed=ap[1],distance_speed=di[2],actual_speed=di[1],distance_old_target=di[3],distance=st[1],position=en[1:],ordered_delta=(delta if hz==50 and ordered else None)))
result=dict(kernel='ordered-engine-400' if ordered else 'native-calibrated-fifths',rate=hz,rows=rows,scaled_acceleration_sum=sum(r['scaled_acceleration'] for r in rows),old_new_mismatch=[r['tick'] for r in rows if r['distance_speed']-r['old_local_speed']!=r['scaled_acceleration']],applied_mismatch=[r['tick'] for r in rows if r['distance_speed']!=r['applied_speed']],distance_sum=sum(r['distance'] for r in rows),final_carry=carry,scope='All observed distance quotients and carries reproduce the live code; compare speed-update order before selecting any correction.')
(p/'distance-order.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
