from pathlib import Path
import shutil,subprocess,difflib
root=Path(__file__).resolve().parents[1];src=root/'tmp/step8-emulator/fs-uae';dst=root/'tmp/step9-emulator/fs-uae'
assert not dst.exists();shutil.copytree(src,dst,symlinks=True)
patch=[]
def change(file,fn):
 p=dst/file;old=p.read_text();new=fn(old);assert old!=new;p.write_text(new);patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+file,tofile='b/'+file))
change('src/tfx_profile.h',lambda s:s.replace('#include <map>','#include <map>\n#include <vector>\n#include <array>\nstatic std::vector<std::array<unsigned,7>> tfx_math;').replace('tfx_stats.clear();','tfx_math.clear();tfx_stats.clear();').replace(' fclose(f);',' for(auto &r:tfx_math)fprintf(f,"math,%u,%u,%u,%u,%u,%u,%u\\n",r[0],r[1],r[2],r[3],r[4],r[5],r[6]);\n fclose(f);'))
change('src/newcpu.cpp',lambda s:s.replace('if(tp){ts->n++;', '''if(tp){
 unsigned off=tfx_pc-tfx_base;
 if(off==0x50f82 || off==0x5169e || off==0x516b6 || off==0x517a4 || off==0x517f2 || off==0x5183c) {
  uae_u32 a,b,c; fpdata tmp=regs.fp[off==0x517a4?1:7]; fpp_from_exten_fmovem(&tmp,&a,&b,&c);
  tfx_math.push_back({tfx_frame,off,0,a,b,c,regs.fpcr});
 }
 if(off==0x50f86 || off==0x516a2 || off==0x516ba || off==0x517a8 || off==0x517f6 || off==0x51840) {
  uae_u32 a,b,c; fpdata tmp=regs.fp[off==0x517a8?5:0]; fpp_from_exten_fmovem(&tmp,&a,&b,&c);
  tfx_math.push_back({tfx_frame,off-4,1,a,b,c,regs.fpcr});
 }
 ts->n++;'''))
(root/'tools/step9-math-observer.patch').write_text(''.join(patch))
with (dst.parent/'build.log').open('w') as f:subprocess.run(['make','-j4'],cwd=dst,stdout=f,stderr=subprocess.STDOUT,check=True)
