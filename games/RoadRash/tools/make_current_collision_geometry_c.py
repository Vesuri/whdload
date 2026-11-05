from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
src=root.parents[1]/'src';dst=root/'tmp/c-current-collision-geometry-source'
shutil.copytree(src,dst,dirs_exist_ok=True)
p=dst/'RoadRashHD.s';s=p.read_text().replace('\tIFD C_PHYSICS_FAST\n; Copy after C patches','\tbsr step_collision_geometry_init\n\tIFD C_PHYSICS_FAST\n; Copy after C patches',1);p.write_text(s)
p=dst/'simulation.s';s=p.read_text().replace('step_collision_objects:\n\tjsr $8970e','step_collision_objects:\n\tbsr step_collision_geometry_code',1)
patch=(root/'tmp/c-road-collision-compact-build/candidate.patch').read_text()
helper=patch.split('+step_collision_geometry_init:',1)[1].split('+\tENDC',1)[0]
helper='step_collision_geometry_init:'+''.join(line[1:]+'\n' for line in helper.splitlines() if line.startswith('+'))
s=s.replace('step_collision_objects:',helper+'\nstep_collision_objects:',1);p.write_text(s)
