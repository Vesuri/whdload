from pathlib import Path
import re,subprocess
root=Path.cwd(); src=root/'src'
listing=(root/'tmp/visual-final-build/RoadRash.lst').read_text(errors='replace')
symbols=set(re.findall(r'^([A-Za-z_]\w*)\s+(?:E|00):[0-9A-F]+',listing,re.M))
original=subprocess.check_output(['git','show','roadrash:src/RoadRashHD.s'],text=True)
symbols.update(re.findall(r'^(C_\w+|REFERENCE_MOTION|POSE_PREDICT_MEASURED|STEP_NO_HASH)\s*=',original,re.M))
# Resolve only development feature switches. Preserve numeric assembly assertions
# and assembler-specific conditionals. Runtime PL_IFC2 is untouched.
def known(s):return s.startswith(('C_','VERIFY','public_ref_')) or s in ('REFERENCE_MOTION','POSE_PREDICT_MEASURED','STEP_NO_HASH','STEP_EXTRAPOLATE','STEP_HASH_RING','STEP_CAPTURE_END')
for p in src.glob('*.s'):
 if p.name.startswith('verify'):continue
 out=[];stack=[];active=True
 for line in subprocess.check_output(['git','show','roadrash:'+str(p.relative_to(root))],text=True).splitlines(True):
  m=re.match(r'^\s*(IFD|IFND|IFEQ|IFNE|IFGT|IFGE|IFLT|IFLE|IFC|IFNC)\s+([^;\s]+)',line,re.I)
  if m:
   op,s=m.groups();op=op.upper();resolved=op in ('IFD','IFND') and known(s)
   choice=(s in symbols) if op=='IFD' else (s not in symbols)
   stack.append((active,resolved,choice))
   if resolved:active=active and choice
   elif active:out.append(line)
   continue
  if re.match(r'^\s*ELSE\b',line,re.I):
   parent,resolved,choice=stack[-1]
   if resolved:active=parent and not choice
   elif active:out.append(line)
   continue
  if re.match(r'^\s*ENDC\b',line,re.I):
   parent,resolved,choice=stack.pop()
   if not resolved and active:out.append(line)
   active=parent;continue
  if active:out.append(line)
 assert not stack,p
 p.write_text(''.join(out))
# The header formerly derived the now-resolved build switches.
p=src/'RoadRashHD.s';s=p.read_text();start=s.index('\n',s.index('INCLUDE\twhdmacros.i'))
end=s.index('\tIFD BARFLY')
s=s[:start+1]+'\n'+s[end:];p.write_text(s)
# Remove reports, diagnostic sources and the local release/validation packager.
for p in src.iterdir():
 if p.suffix=='.md' or p.name in ('memory-assets.json','package_release.py') or p.name.startswith('verify'):
  p.unlink()
