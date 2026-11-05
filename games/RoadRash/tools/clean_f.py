from pathlib import Path
import shutil
root=Path('src');shutil.copytree(root,'tmp/f-pre-clean-source')
p=root/'cpu_work.s';s=p.read_text()
for name in ['projection','patterns','geometry']:s=s.replace(f' bsr.w f_{name}_init\n','')
a=s.index('; F2a prototype:');b=s.index('; Cache only the dedicated',a);s=s[:a]+s[b:]
a=s.index('; F1a prototype:');b=s.index('; Native/Chip fallback:',a);s=s[:a]+s[b:]
s=s.replace('; F1c: merge each pair of unrolled plane fills, keeping native clipping.\n; Called only after CUSTOM2/public placement validation, before cache flush.\n; Rewrite relocated jump tables after their HUNK fixups. No per-frame patches.','; F: CPU work reduction. Public entry runs after CUSTOM2/placement validation.\n; The caller flushes caches after all one-time patches; no per-frame code writes.')
s=s.replace('f_span_init:', '; F1c: paired plane fills; preserve clipping and rewrite relocated jump tables.\nf_span_init:',1)
p.write_text(s)
p=root/'RoadRashHD.s';s=p.read_text();s=s.replace('\tinclude\t"projection_reciprocal.s"\n','').replace(' include "projection_reciprocal.s"\n','');p.write_text(s)
(root/'projection_reciprocal.s').unlink()
for name in ['f-div-v3-frames','f-sort-frames']:
 a=Path('tmp/e-cpu-frames');b=Path('tmp')/name
 assert all(p.read_bytes()==(a/p.name).read_bytes() for p in b.glob('frame-*.bin'));print(name,'64 exact')
shutil.copytree(root,'tmp/f-final-source')
p=Path('tools/finish_final_e.py');s=p.read_text().replace('e-final','f-final').replace('27754','27830').replace('timeout=600','timeout=1800');Path('tools/finish_final_f.py').write_text(s)
p=Path('tools/run_scenes_f.py');s=p.read_text().replace('f-scenes-v1','f-scenes-final').replace("DEBUG_PORT='27810'","DEBUG_PORT='27832'").replace('timeout=600','timeout=1800');Path('tools/run_scenes_final_f.py').write_text(s)
