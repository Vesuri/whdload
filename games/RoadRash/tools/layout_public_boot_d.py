from pathlib import Path
import shutil
src=Path('tmp/d-public-boot-hardened-v2-source');dst=Path('tmp/d-public-boot-layout-source');shutil.copytree(src,dst)
p=dst/'public_loader.s';s=p.read_text();code,tables=s.split('public_loader_refs:',1)
for label,reg in [('public_loader_check','a0'),('public_loader_refs','a6'),('public_loader_relative','a6')]:
 code=code.replace(f' lea {label}(pc),{reg}',f' lea _base(pc),{reg}\n adda.l #{label}-_base,{reg}')
p.write_text(code);tables='public_loader_refs:'+tables
p=dst/'public_boot.s';s=p.read_text();code,rest=s.split('public_boot_title_info:',1)
parts=rest.split('public_boot_title_refs:',1);code+='public_boot_title_info:'+parts[0];rest='public_boot_title_refs:'+parts[1]
a,rest=rest.split('public_boot_intro_info:',1);tables+=a
parts=rest.split('public_boot_intro_refs:',1);code+='public_boot_intro_info:'+parts[0];rest='public_boot_intro_refs:'+parts[1]
a,rest=rest.split('; a0: six-byte',1);tables+=a
rest='; a0: six-byte'+rest;a,b=rest.split('public_loader_check:',1);code+=a;tables+='public_loader_check:'+b
p.write_text(code);(dst/'public_boot_tables.s').write_text(tables)
p=dst/'RoadRashHD.s';s=p.read_text();s+='\n IFD C_PUBLIC_MAIN\n include public_boot_tables.s\n ENDC\n';p.write_text(s)
