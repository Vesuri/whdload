# Execute within the native UI harness via its exec operation. No guest writes.
def repair_charge(label):
 modal_table=table if 'table' in globals() else val('*(unsigned int*)0x197b0')*4
 h176=val(f'*(unsigned int*){modal_table+176*4}')*4+4
 h179=val(f'*(unsigned int*){modal_table+179*4}')*4+4
 helper=h179+0x9f4;caller=h176+0xeb4
 assert val(f'*(unsigned short*){helper}')==0x4e56
 assert val(f'*(unsigned short*){h176+0xeae}')==0x4eb9
 assert val(f'*(unsigned int*){h176+0xeb0}')==helper
 cmd('delete');cmd(f'break *{helper}');cmd(f'condition $bpnum *(unsigned int*)$sp == {caller}');cmd(f'break *{native(0x2482a)}');vbl_bp=val('$bpnum');cmd('ignore $bpnum 29');cmd('monitor input JOY1_FIRE_BUTTON 1');assert 'Breakpoint' in cmd('continue');cmd('monitor input JOY1_FIRE_BUTTON 0')
 if val('$pc')!=helper:
  cmd(f'ignore {vbl_bp} 999');assert 'Breakpoint' in cmd('continue')
 assert val('$pc')==helper
 amount=val('*(unsigned int*)($sp+4)');returned=val('*(unsigned int*)$sp')
 _,before=snapshot(label+'-before');cmd('delete');cmd(f'break *{returned}');assert 'Breakpoint' in cmd('continue');_,after=snapshot(label+'-after')
 report.setdefault('repair_charges',[]).append(dict(label=label,tenths_argument=amount,caller='menu h176+$eae',before=before,after=after));save()
