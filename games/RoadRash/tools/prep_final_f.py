from pathlib import Path
for d in ['src','tmp/f-final-source']:
 p=Path(d)/'RoadRashHD.s';s=p.read_text().replace('\tbsr step_object_fast_init','\tlea _base(pc),a0\n\tadda.l #step_object_fast_init-_base,a0\n\tjsr (a0)');p.write_text(s)
p=Path('tools/functional_complete_e.py');s=p.read_text().replace('e-020-gate-build','f-functional-build').replace('e-functional-complete','f-functional').replace('27760','27840');Path('tools/functional_f.py').write_text(s)
p=Path('tools/dcache_e.py');s=p.read_text().replace('e-020-gate-build','f-functional-build').replace('e-final-dcache','f-final-dcache').replace('27765','27845');Path('tools/dcache_f.py').write_text(s)
p=Path('tools/extra_e.py');s=p.read_text().replace('e-final-build','f-functional-build').replace('e-final-extra','f-final-extra').replace('27767','27847');Path('tools/extra_f.py').write_text(s)
