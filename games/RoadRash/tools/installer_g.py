import sys
sys.exit('installer_g.py needs the retired harness launcher (a private copy of amiga/run.sh with extra drives and its own startup-sequence); see docs/development.md')
from pathlib import Path
import re,shutil
root=Path.cwd();base=root/'tmp/g-installer-native';base.mkdir(exist_ok=True);game=base/'fixture';game.mkdir(exist_ok=True)
usr=root/'release';source=(usr/'Install').read_text(encoding='latin1')
# Balanced parser with spans: tests replace only interaction, not file operations.
def spans(text):
 stack=[];out=[];i=0
 while i<len(text):
  if text[i]==';':
   n=text.find('\n',i);i=len(text) if n<0 else n;continue
  if text[i]=='"':
   i+=1
   while i<len(text) and text[i]!='"':
    if text[i]=='\\':i+=1
    i+=1
   assert i<len(text);i+=1;continue
  if text[i]=='(':stack.append(i)
  if text[i]==')':
   assert stack;start=stack.pop();out.append((start,i+1,text[start:i+1]))
  i+=1
 assert not stack;return out
spans(source)
for name in ['Install.info','Manual','Manual.info','Readme','Readme.info']:shutil.copy2(usr/name,game/name)
shutil.copy2(root/'tmp/g-release-build/RoadRash.slave',game/'RoadRash.slave')
shutil.copy2(Path.home()/'.local/share/amiga/Installer43/Installer',game/'Installer')
for d in ['disk1','disk1alt','disk2/data','Install Test']:(game/d).mkdir(parents=True,exist_ok=True)
(game/'disk1/first').write_text('disk one root\n');(game/'disk1alt/first').write_text('disk one root\n');(game/'disk2/data/second').write_text('disk two data\n')
commands=['FailAt 999','DF0:C/Assign C: DF0:C','DF0:C/Assign LIBS: DF0:Libs','DF0:C/Assign ENV: RAM:','DF0:C/Assign ENVARC: RAM:','Path DH1: ADD','Stack 65536','CD DH1:','Assign rr1: DH1:disk1','Assign "Road Rash:" DH1:disk1','Assign roadrash: DH1:disk2']
for ix,(label,icon) in enumerate(list((l,i) for l in [0,1] for i in ['romicon','newicon','coloricon','glowicon','exoticon']) + [(0,'romicon'),(0,'romicon')]):
 name=f'case{ix}';d=game/name;d.mkdir(exist_ok=True)
 for f in game.iterdir():
  if f.is_file() and f.name not in ['Installer']:shutil.copy2(f,d/f.name)
 shutil.copy2(usr/f'RoadRash.{icon}',d/f'RoadRash.{icon}')
 changes=[]
 for a,b,expr in spans(source):
  head=expr[1:].split(None,1)[0].rstrip(')')
  if head=='askchoice':changes.append((a,b,str(label) if 'How is disk #1' in expr else '0'))
  if head=='askdir':changes.append((a,b,f'"DH1:Install Test/{name}"'))
  if head=='askbool':changes.append((a,b,'0' if ix==11 else '1'))
  if head in ['message','openwbobject','closewbobject']:changes.append((a,b,'("")'))
  if head=='exit':changes.append((a,b,'(exit (quiet))'))
 s=source
 for a,b,new in sorted(changes,reverse=True):s=s[:a]+new+s[b:]
 (d/'Install').write_bytes(s.encode('latin1'));(game/f'Install Test/{name}').mkdir(exist_ok=True)
 if ix>=10:
  existing=game/f'Install Test/{name}/RoadRash';existing.mkdir(exist_ok=True)
  (existing/'saved-game').write_text('keep me unless replacement accepted')
  (existing.with_suffix('.info')).write_bytes(b'old drawer icon')
 commands += [f'CD DH1:{name}' ,f'DH1:Installer Install APPNAME RoadRash MINUSER NOVICE DEFUSER NOVICE NOPRETEND NOLOG NOPRINT LOGFILE DH1:{name}.log',f'Echo "returned" >DH1:{name}.done']
commands += ['Echo "done" >DH1:all.done']
commands=[c for c in commands if not c.startswith(('Assign rr1:', 'Assign \"Road Rash:', 'Assign roadrash:'))]
(base/'startup').write_text('\n'.join(commands)+'\n')
run=(root/'tmp/dev/amiga/run.sh').read_text().replace('. "$(dirname "$0")/env.sh"','. "'+str(root/'tmp/dev/amiga/env.sh')+'"').replace('cd "$HARNESS_ROOT/amiga"','cd "'+str(base)+'"')
run=run.replace('rm -f "$RUN"/state/*.uss','cp "'+str(base/'startup')+'" "$DH0/s/startup-sequence"\nrm -f "$RUN"/state/*.uss')
run=run.replace('--hard_drive_0="$DH0"', '--hard_drive_2="'+str(game/'disk1')+'" --hard_drive_2_label="rr1" --hard_drive_3="'+str(game/'disk1alt')+'" --hard_drive_3_label="Road Rash" --hard_drive_4="'+str(game/'disk2')+'" --hard_drive_4_label="roadrash" --hard_drive_0="$DH0"')
(base/'run.sh').write_text(run)
(base/'amiga/run.sh').write_text(run)
print(base)
