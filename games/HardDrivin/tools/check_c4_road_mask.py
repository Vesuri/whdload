from pathlib import Path
import ctypes as C,json,os,struct,subprocess
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
s=Path('tools/c4_terrain_road.s').read_text()
body=s[s.index('_private_road_mask:'):]
stem=Path('tmp/c4-road-mask')
stem.with_suffix('.s').write_text(' org $10000\n'+body+'\n_private_road_selected equ $11000\n')
subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
write(0x10000,stem.with_suffix('.bin').read_bytes())
a4=0x40000;count=0
try:
 for course in [0,1]:
  for selected in [0,1,2,3]:
   for cursor in range(10):
    for gaps in range(4):
     write(0x22000,bytes(0x2000))
     for off,val in [(0x98e0,0x22000),(0xaf26,0x22000+200),(0x9952,0x23000),(0xaf2a,0x23000+200)]:pack(a4+off-65536,'I',val)
     base=0x22000+course*0x1000
     pack(a4+0x9950-65536,'B',course);pack(a4+0x98e4-65536,'I',base+cursor*20);pack(0x11000,'H',selected)
     if selected in [1,2]:
      first=base+(cursor+selected-3)*20
      pack(first+18,'H',0x408 if gaps&2 else 8);pack(first+38,'H',0x409 if gaps&1 else 9)
     expected=(3^gaps) if selected in [1,2] and 2<=cursor<=7 else 0
     reg(17,0x2000);reg(5,a4);reg(8,0x4f000);pack(0x4f000,'I',0x19000)
     ok(u.uc_emu_start(h,0x10000,0x19000,1000000,1000))
     assert reg(18)==0x19000 and reg(8)==0x4f004
     assert reg(11)==expected,(course,selected,cursor,gaps,reg(11),expected)
     count+=1
 report=dict(passed=True,cases=count,scope='Actual 68000 road-record selection and gap mask for both course lists, two native candidate indices, invalid indices, both list boundaries and all four gap combinations. Boundary crossing deliberately rejects new eligibility; this does not validate whole-course traversal.')
 Path('tmp/c4-road-mask-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
