#!/usr/bin/env python3
"""Run the terminating WHDLoad cache audit outside measured baseline boots."""
import argparse,json,os,re,shutil,time
from pathlib import Path
from capture_demo import ROOT,RUN,command
from capture_session import Session
from machine_profiles import PROFILES
p=argparse.ArgumentParser();p.add_argument('profile',choices=PROFILES);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/('s2-cache-'+a.profile);out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s2-cache-audit.slave',out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0)
s.env['WHD_ARGS']='FILELOG LogBuffer=32768'
try:
 s.start(tag='audit');log=None
 for _ in range(120):
  for f in (RUN/'dh1').rglob('.whdl_log'):
   if b'HD_CACHE' in f.read_bytes():log=f;break
  if log:break
  time.sleep(1)
 assert log,'cache audit log did not flush'
 text=log.read_text(encoding='latin1');(out/'whdl.log').write_text(text);m=re.search(r'HD_CACHE attn=([0-9a-fA-F]+) setup=([0-9a-fA-F]+) cache_api=([0-9a-fA-F]+) cacr=([0-9a-fA-F]+)',text);assert m,text
 (out/'cache.json').write_text(json.dumps(dict(profile=a.profile,**{k:int(v,16) for k,v in zip(['attn','setup','cache_api','cacr'],m.groups())}),indent=2)+'\n')
 shutil.copyfile(RUN/'fsuae/Cache/Logs/debug.uae',out/'emulator.uae');print(a.profile,m.groups(),flush=True)
finally:s.close()
