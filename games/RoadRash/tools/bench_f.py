import os,sys,subprocess,shutil,json
from pathlib import Path
root=Path.cwd();kind=sys.argv[1];port=sys.argv[2];tag=sys.argv[3] if len(sys.argv)>3 else kind;src=root/f'tmp/f-bench-{tag}-source';build=root/f'tmp/f-bench-{tag}-build'
shutil.copytree(root/'src',src)
p=src/'cpu_work.s';s=p.read_text()
for name in ['span','edge','dda','dispatch','saves','hud','geometry','patterns','projection','sort']:
 if kind!='all' and name not in kind.split(','):s=s.replace(f' bsr.w f_{name}_init',' nop\n nop',1)
p.write_text(s)
env=dict(os.environ,RR_SOURCE=str(src),RR_BUILD_OUT=str(build));subprocess.run(['bash','tools/build.sh'],env=env,check=True,stdout=subprocess.DEVNULL)
env=dict(os.environ,E_PORT=port)
subprocess.run([sys.executable,'tools/run_checks_e.py',f'tmp/f-bench-{tag}',str(build/'RoadRash.slave'),'a1200-fast','030-50','040-25'],env=env,check=True)
