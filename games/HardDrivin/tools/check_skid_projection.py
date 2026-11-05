import json,re,sys
from pathlib import Path
for name in sys.argv[1:]:
 out=Path('tmp/prof')/name;before={};after={};mode=None;count=fields=0;changing=0;previous_speed=None
 for line in (out/'events.log').read_text().splitlines():
  m=re.fullmatch(r'(YPIN|YPOUT|ZPIN|ZPOUT|PIN|POUT) ([-0-9 ]+)',line)
  if m:
   tag=m[1];axis=tag[0] if tag[0] in 'YZ' else 'X';r=list(map(int,m[2].split()))
   (before if tag.endswith('PIN') else after)[axis]=r
  m=re.fullmatch(r'MODE (PIN|POUT) ([-0-9 ]+)',line)
  if not m:continue
  r=list(map(int,m[2].split()))
  if m[1]=='PIN':assert mode is None;mode=r;continue
  assert mode is not None and set(before)==set(after)=={'X','Y','Z'}
  assert mode[1:]==r[1:]
  if mode[1]:
   assert mode[2:]==[15,0],mode
   for axis in before:
    a,b=before[axis],after[axis]
    assert a[2]==a[3]==b[2] and a[5]==a[6]==b[5]==b[6],(axis,a,b)
   speed=before['X'][10];changing+=previous_speed is not None and speed!=previous_speed;previous_speed=speed
   count+=1;fields+=before['X'][8]
  else:previous_speed=None
  before={};after={};mode=None
 assert mode is None and count and changing
 result=dict(passed=True,skid_position_updates=count,integrated_skid_fields=fields,scalar_velocity_changes_while_skidding=changing,all_three_native_vectors_and_fractional_corrections_held=True)
 (out/'skid-position-check.json').write_text(json.dumps(result,indent=2)+'\n');print(name,result)
