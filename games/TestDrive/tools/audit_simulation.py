#!/usr/bin/env python3
"""Audit declared VERIFY/optional patch ranges against pinned original TD hunks."""
import hashlib,json,re,struct
from pathlib import Path
import capstone
from harness import ROOT
SOURCE=ROOT/'src'
def ranges():
 result=[]
 for name in ['TestDriveHD.s','simulation-verify.s','simulation-patches.i','render-patches.i']:
  for h,off,n,gate,label in re.findall(r'; (?:VERIFY|SIM|RENDER)_RANGE (root|h4) ([0-9a-f]+) (\d+) (\S+) (\w+)',(SOURCE/name).read_text()):
   result.append(dict(hunk=h,offset=int(off,16),size=int(n),gate=gate,label=label))
 # Existing phase-4 root patches: grouped by whole replaced instructions.
 result += [dict(hunk='root',offset=a,size=n,gate='C3' if a==0x230 else 'C2|C3',label=l) for a,n,l in [(0x230,6,'verify_demo_rng'),(0x5314,8,'fixed_seed'),(0x5334,6,'beam_removed')]]
 # Every overlay patch must have exactly one declaration; a missing range
 # must fail before disabled-byte checks can silently omit it.
 overlay=(SOURCE/'simulation-verify.s').read_text().split('verify_overlay_patches:',1)[1].split('verify_race_entry:',1)[0]
 overlay += (SOURCE/'TestDriveHD.s').read_text().split('instrument_patches:',1)[1].split('instrument_car:',1)[0]
 overlay += (SOURCE/'simulation-patches.i').read_text()
 overlay += (SOURCE/'render-patches.i').read_text()
 actual={(int(a,16),label,6+int(extra or 0)) for a,label,extra in re.findall(r'^\s*PL_P(?:S(?:S)?)? \$([0-9a-f]+),(\w+)(?:,(\d+))?$',overlay,re.M)}
 actual |= {(int(a,16),'current_x',4) for a in re.findall(r'^\s*PL_L \$([0-9a-f]+),\$946ca898',overlay,re.M)}
 actual |= {(int(a,16),'nop',int(n)) for a,n in re.findall(r'^\s*PL_NOP \$([0-9a-f]+),(\d+)',overlay,re.M)}
 declared={(r['offset'],r['label'],r['size']) for r in result if r['hunk']=='h4'}
 assert actual==declared,('unlisted or stale overlay range',actual^declared)
 return result

def gate_on(g,opts):
 if g=='ALL':return True
 if g=='C2R':return bool(opts['C2'] and not opts['C1']&16)
 if g=='always':return bool(opts['C1']&2 or opts['C3'] or opts['C4'] or opts['C5'])
 if g=='C1.1':return bool(opts['C1']&2)
 if g=='C2|C3':return bool(opts['C2'] or opts['C3'])
 if g=='C3!C2':return bool(opts['C3'] and not opts['C2'])
 return bool(opts[g])

def originals():
 b=(ROOT/'tmp/game/TestDrive_v1.3_0089/TestDrive/data/TD').read_bytes()
 assert hashlib.sha256(b).hexdigest()=='dd5b9608d64de145a6138c99d175f148939bd8e8c37d793631314a50c9d606db'
 return {'root':b[0x28:0x7c34],'h4':b[0xb9dc:0x15ff8]}
def validate(rs,bs):
 md=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_BIG_ENDIAN|capstone.CS_MODE_M68K_000)
 incoming=[]
 for i,r in enumerate(rs):
  h,a,n=r['hunk'],r['offset'],r['size'];b=bs[h]
  assert a%2==n%2==0 and n>=2
  for q in rs[:i]:
   if q['hunk']!=h or max(a,q['offset'])>=min(a+n,q['offset']+q['size']):continue
   assert (a,n)==(q['offset'],q['size']) and {r['gate'],q['gate']}=={'C2','C3!C2'}, 'overlapping hooks'
  ins=list(md.disasm(b[a:a+n],a));assert sum(x.size for x in ins)==n and all(x.mnemonic!='dc.w' for x in ins),'split/invalid instruction'
  for p in range(0,len(b)-6,2):
   w=int.from_bytes(b[p:p+2],'big');t=None
   if w>>12==6:
    d=struct.unpack('b',b[p+1:p+2])[0]
    if not d:d=struct.unpack('>h',b[p+2:p+4])[0]
    t=p+2+d
   elif w&0xf0f8==0x50c8 or w in (0x4eba,0x4efa):t=p+2+struct.unpack('>h',b[p+2:p+4])[0]
   elif w in (0x4eb9,0x4ef9):t=int.from_bytes(b[p+2:p+6],'big')
   if t is not None and a<=t<a+n:
    assert t==a,f'{h}:{p:x} enters hook interior {t:x}'
    incoming.append(dict(hunk=h,source=p,target=t))
 return incoming
if __name__=='__main__':
 rs=ranges();bs=originals();incoming=validate(rs,bs)
 print(json.dumps(dict(status='PASS',ranges=rs,incoming=incoming,limit='word-aligned direct candidates; indirect targets not proven'),indent=2))
