from pathlib import Path
p=Path('src/TFXHD.s');s=p.read_bytes().decode();assert 'flat_two_blocks_040:' not in s
code=['; Unrolled two-block flat span; retains original colour/edge calculations.','flat_two_blocks_040:']
for group in range(2):
 for i in range(4):
  off=-8000*i
  ea='(a1)' if off==0 else f'{off}(a1)'
  code += ['        add.w d1,d1','        subx.l d6,d6',f'        bfins d6,{ea}{{d3:d4}}',f'        bfins d6,{off+4}(a1){{0:d5}}']
 code += ['        lea -32000(a1),a1']
code += ['        add.w d1,d1','        jmp (a6)','']
s=s.replace('pl_fpu_new_render_040:\r\n','\r\n'.join(code)+'\r\npl_fpu_new_render_040:\r\n');s=s.replace('        ; Keep original ScanFillDown: the equivalent port measured slower on 040.','        PL_P    $6c5d4,flat_two_blocks_040\r\n        ; Keep original ScanFillDown: the equivalent port measured slower on 040.')
p.write_bytes(s.encode())
