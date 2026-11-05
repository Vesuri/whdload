# Observe native transport day addition; no guest memory/register writes.
def travel_charge(label):
 modal_table=table if 'table' in globals() else val('*(unsigned int*)0x197b0')*4
 h167=val(f'*(unsigned int*){modal_table+167*4}')*4+4
 before_pc=h167+0x84;after_pc=h167+0xaa
 assert val(f'*(unsigned short*){before_pc}')==0x42ae
 cmd('delete');cmd(f'break *{before_pc}');cmd(f'break *{native(0x2482a)}');vbl=val('$bpnum');cmd('ignore $bpnum 29');cmd('monitor input JOY1_FIRE_BUTTON 1');cmd('continue');cmd('monitor input JOY1_FIRE_BUTTON 0')
 if val('$pc')!=before_pc:cmd(f'ignore {vbl} 1999');cmd('continue')
 assert val('$pc')==before_pc
 days=val('*(unsigned int*)($a6-8)');_,before=snapshot(label+'-before')
 cmd('delete');cmd(f'break *{after_pc}');cmd('continue');assert val('$pc')==after_pc
 _,after=snapshot(label+'-after')
 report.setdefault('travel_charges',[]).append(dict(label=label,days=days,clock_loop='menu h167+$84..$aa',before=before,after=after));save()
