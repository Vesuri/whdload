from pathlib import Path
import shutil
src=Path('src');dst=Path('tmp/c-runtime-source');dst.mkdir(exist_ok=True)
for p in src.iterdir():
 if p.is_file():shutil.copyfile(p,dst/p.name)
p=dst/'RoadRashHD.s';s=p.read_text();s=s.replace('\tIFD VERIFY\n\tIFD VERIFY_C_STEP\nC_STEP_BUILD = 1\n\tENDC\n\tENDC', '\tIFD C_SIMULATION\nC_STEP_BUILD = 1\nC_RUNTIME_ONLY = 1\nSTEP_NO_HASH = 1\n\tELSE\n\tIFD VERIFY\n\tIFD VERIFY_C_STEP\nC_STEP_BUILD = 1\n\tENDC\n\tENDC\n\tENDC',1)
s=s.replace('\tIFD VERIFY\n\tdc.l\tWHDLTAG_ATTNFLAGS_GET\nverify_attn\tdc.l\t0\n\tENDC','\tIFD C_STEP_BUILD\n\tdc.l WHDLTAG_ATTNFLAGS_GET\nverify_attn dc.l 0\n\tELSE\n\tIFD VERIFY\n\tdc.l WHDLTAG_ATTNFLAGS_GET\nverify_attn dc.l 0\n\tENDC\n\tENDC')
s=s.replace('\tIFD VERIFY\n\tIFD VERIFY_C_STEP\n\tinclude\tverify_c_step.s\n\tENDC\n\tENDC','\tIFD C_STEP_BUILD\n\tIFND VERIFY\nverify_c_selection:\n\tdc.b "RRCSEL01"\n\tdc.l 0,0,0,0\n\tENDC\n\tinclude verify_c_step.s\n\tENDC')
p.write_text(s)
p=dst/'verify_c_step.s';s=p.read_text();start=s.index('\tlea step_stats(pc),a0\n\tIFD STEP_CAPTURE_END');end=s.index('\n.done:\n\tIFD VERIFY_C_LATENCY',start);s=s[:start]+'\tIFND C_RUNTIME_ONLY\n'+s[start:end]+'\n\tENDC'+s[end:]
start=s.index('step_snapshot:\n');end=s.index('\nstep_start_sprite:',start);s=s[:start]+'\tIFND C_RUNTIME_ONLY\n'+s[start:end]+'\n\tENDC\n'+s[end:];p.write_text(s)
print(dst.resolve())
