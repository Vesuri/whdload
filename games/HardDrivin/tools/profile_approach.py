#!/usr/bin/env python3
"""Capture a 500-field trace within a native gameplay window from a fresh boot."""
import argparse,json,os,re,shutil,subprocess,sys
from pathlib import Path
from capture_demo import ROOT,command,sha
from capture_session import Session
from window_metrics import report
from machine_profiles import PROFILES
p=argparse.ArgumentParser();p.add_argument('profile',choices=PROFILES);p.add_argument('window',choices=['A','B','attract']);p.add_argument('name');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;assert out.parent==ROOT/'tmp/prof'
if out.exists() and (out/'trace.sha256').exists() and (out/'trace-fingerprints.json').exists():
 old=json.loads((out/'metadata.json').read_text());metrics=json.loads((out/'window-metrics.json').read_text())
 assert old['layout']['profile']==a.profile and old['trace_window']['name']==a.window
 assert old['emulator_sha256']==sha(os.environ['PROFILE_FSUAE'])
 assert old['slave_sha256']==sha(ROOT/'tmp/build'/('HardDrivin-verify.slave' if a.window=='attract' else 'HardDrivin-drive.slave'))
 assert metrics['fields']==(1000 if a.window=='attract' else 500)
 assert (out/'trace.bin.zst').exists()
 print('ALREADY COMPLETE',a.name,flush=True);sys.exit(0)
out.mkdir(exist_ok=False)
mode='attract' if a.window=='attract' else 'drive';build='HardDrivin-verify.slave' if mode=='attract' else 'HardDrivin-drive.slave';listing=ROOT/'tmp/build'/('verify.lst' if mode=='attract' else 'drive.lst');shutil.copyfile(ROOT/'tmp/build'/build,out/'slave.slave');shutil.copyfile(listing,out/'slave.lst')
s=Session(out,a.profile,out/'slave.slave',0x10844 if mode=='attract' else 0x10ed4)
try:
 print('BOOT PROFILE',a.name,flush=True);s.boot()
 # Stop after publication just before the desired first full trace field. B's
 # sample [4300,4800) spans the A500 jump and crash; A begins with race field 1.
 before=0 if a.window=='A' else 1899 if a.window=='B' else None
 if before:
  base=s.layout['code_base'];command(f'''gdb break *{base+0x3f2:#x}
set $hd_skip=0
while $hd_skip < {before}
continue
set $hd_skip=$hd_skip+1
end
delete''')
 n=1000 if mode=='attract' else 500
 (out/'profile-response.txt').write_text(command(f'profile {n} {out}/trace.bin'))
 s.metadata['trace_window']=dict(name=a.window,fields=n,first_full_race_field=1 if a.window=='A' else 1900 if a.window=='B' else None)
 (out/'metadata.json').write_text(json.dumps(s.metadata,indent=2)+'\n');s.dump_banks('after')
finally:s.close()
r=report(out,listing)
# The trace's VBL-leading swap precedes the input-publication boundary used by
# the drive event logger; physics after that VBL belongs to the new race field.
baseline=ROOT/'tmp/prof'/('s2-'+a.profile+'-'+('attract1' if mode=='attract' else 'drive'))/'baseline.json'
if baseline.exists():b=json.loads(baseline.read_text())
elif a.profile=='a500' and mode=='drive':
 old=ROOT/'tmp/prof/drive-a500-jump1/capture.log';b=dict(events=[dict(offset=int(o,16),field=int(f)) for o,f in re.findall(r'^EVENT ([0-9a-f]+) (\d+)$',old.read_text(),re.M)])
else:raise FileNotFoundError(baseline)
first=0 if a.window in ['A','attract'] else 1899
expected=[sum(e['offset']==0xb4 and e['field']==f for e in b['events']) for f in range(first,first+n)]
if r['instruction_timing_supported']:
 actual=[f['swaps'] for f in r['per_field']]
 r['independent_per_field_match']=expected==actual
 r['independent_mismatch_fields']=[i for i,(x,y) in enumerate(zip(expected,actual)) if x!=y]
 assert sum(expected)==sum(actual), 'trace changed whole-window swap count'
 if expected!=actual:r['limitations'].append('Independent breakpoint run has the same swap total but different per-field timing; inspect fresh trace repeat before acceptance.')
r['independent_swaps']=sum(expected);r['independent_swap_first_field']=first;r['independent_counter_validated']=r['instruction_timing_supported'] and r['independent_per_field_match'];(out/'window-metrics.json').write_text(json.dumps(r,indent=2)+'\n')
from trace_fingerprints import fingerprint
fingerprint(out)
digest=sha(out/'trace.bin');subprocess.run(['zstd','-q','-3',str(out/'trace.bin')],check=True);subprocess.run(['zstd','-qt',str(out/'trace.bin.zst')],check=True);(out/'trace.sha256').write_text(digest+'\n');(out/'trace.bin').unlink()
