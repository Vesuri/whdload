from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1];src=root.parents[1]/'src';dst=root/'tmp/c-combined-motion-source';shutil.copytree(src,dst,dirs_exist_ok=True)
p=dst/'RoadRashHD.s';s=p.read_text();prefix='\tIFND VERIFY\nVERIFY_C_ROAD_TIMING = 1\nREFERENCE_MOTION = 1\n\tENDC\n\tIFD C_SIMULATION\nVERIFY_C_ROAD_TIMING = 1\nREFERENCE_MOTION = 1\n\tENDC\n';s=prefix+s
needle='\tIFD C_STEERING\n\tIFD C_ROAD_TIMING';assert needle in s
s=s.replace(needle,'\tIFD REFERENCE_MOTION\n\tPL_P $B4A4,reference_motion_begin\n\tPL_P $B4D2,reference_motion_displacement\n\tENDC\n'+needle,1);p.write_text(s)
p=dst/'simulation.s';p.write_text(p.read_text()+'\n\tIFD REFERENCE_MOTION\n\tinclude reference_motion.s\n\tENDC\n')
patch=(root/'tmp/c-reference-motion-build/source.patch').read_text().split('--- reference_motion.s',1)[1]
body='\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))+'\n';(dst/'reference_motion.s').write_text(body)
