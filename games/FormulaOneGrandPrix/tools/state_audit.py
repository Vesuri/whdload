#!/usr/bin/env python3
"""A3 renderer reachable-store inventory: state_audit.py tmp/REPORT.json.
Requires Capstone 5; reads only the verified original HUNK executable.
The classifications are reviewed findings, not inferred from absence of a net delta.
"""
import sys,json,collections
from pathlib import Path
from state_diff import scratch, digest
from race_profile import GAME
from check_disabled import relocated_original
from slave_inputs import verify
from capstone import *
from capstone.m68k import *
verify();bs=[0x100000,0x200000,0x300000,0x400000];hs=relocated_original(bs)
c=Cs(CS_ARCH_M68K,CS_MODE_M68K_000|CS_MODE_BIG_ENDIAN);c.detail=True
pending=[bs[2]+0x280f6]+[bs[2]+o for o in (0x24180,0x24000,0x23d80,0x23a98)];seen={};unresolved=[];targets=set()
def label(a):
 for n,b in enumerate(bs):
  if b<=a<b+len(hs[n]):return f'h{n}+{a-b:05x}'
 return hex(a)
while pending:
 pc=pending.pop()
 if pc in seen:continue
 h=next((h for h in (0,2) if bs[h]<=pc<bs[h]+len(hs[h])),None)
 if h is None:unresolved.append((label(pc),'outside'));continue
 off=pc-bs[h];i=next(c.disasm(hs[h][off:off+24],pc,count=1),None)
 if i is None or i.mnemonic=='dc.w':unresolved.append((label(pc),'invalid'));continue
 seen[pc]=i;op=i.mnemonic.split('.')[0]
 if op in ('rts','rte','rtr'):continue
 if op in ('jsr','jmp','bsr','bra') or (op.startswith('b') and op not in ('bset','btst','bclr','bchg')) or op.startswith('db'):
  o=i.operands[-1]
  if o.type==M68K_OP_BR_DISP:target=pc+2+o.br_disp.disp
  elif o.type==M68K_OP_MEM and o.address_mode in (16,17):target=o.imm
  elif o.type==M68K_OP_MEM and o.address_mode==11:target=pc+2+o.mem.disp
  elif o.type==M68K_OP_MEM and o.address_mode in (12,13):
   # Sixteen colour-specialized kernels, 24-byte single-word or 96-byte span entries.
   base=pc+2+o.mem.disp
   short_entries=(0x16f8,0x1f6e,0x279e,0x3014,0x1fb3c,0x2030e,0x20dac,0x2162a)
   span_entries=(0x1882,0x20f8,0x2928,0x319e,0x1fcc6,0x20498,0x20f36,0x217b4)
   stride=24 if h==0 and off in short_entries else 96 if h==0 and off in span_entries else None
   if stride is None:unresolved.append((label(pc),i.mnemonic,i.op_str))
   else:pending.extend(base+n*stride for n in range(16))
   target=None
  elif op=='jsr' and o.type==M68K_OP_MEM and o.address_mode==3 and o.reg==14 and h==2 and off in (0x244ee,0x2488c,0x24612):
   target=None # A5 LEAs select the four transform kernels seeded above.
  else:target=None;unresolved.append((label(pc),i.mnemonic,i.op_str))
  if target is not None:
   pending.append(target)
   if op in ('jsr','bsr'):targets.add(target)
  if op in ('jmp','bra'):continue
 pending.append(pc+i.size)

# Classification is by reviewed implementation family, with persistent tick stores
# selected before ordinary renderer work. No default class for unfamiliar code.
def write_class(pc,i):
 h=0 if pc<bs[2] else 2
 off=pc-bs[h]
 o=i.operands[-1]
 if o.address_mode in (3,4,5) and o.reg==16 or o.mem.base_reg==16:
  return 'stack'
 if h==0:
  if 0x25792<=off<0x257c4:return 'tick: shared RNG'
  if 0x1372<=off<0x3794 or 0x1e71c<=off<0x222d0:return 'presentation: pixels, spans and fill workspace'
  if 0x25574<=off<0x2572c:return 'shared math scratch (overwritten before simulation reads)'
 elif h==2:
  if off in (0x28070,0x28078,0x28080) or (0x2a0fa<=off<0x2a418 and o.address_mode==17 and bs[0]+0x3a746<=o.imm<=bs[0]+0x3a820):
   return 'tick: pit animation, camera shake and shared RNG'
  if off==0x29ad8:return 'tick: visible-car debris expiry latch'
  if 0x1e000<=off<0x1fa00:return 'presentation/hardware: blit queue, clear, HUD and pixels'
  if 0x23288<=off<0x26574:return 'presentation: transformed geometry and clipping caches'
  if 0x26574<=off<0x28168:return 'presentation: scene composition, rasterization and mirror workspace'
  if 0x281ae<=off<0x29e16:return 'presentation: object projection, model decoration and pixels'
  if 0x29e7c<=off<0x2a020:return 'presentation: temporary track association and visibility flags'
  if 0x2a05a<=off<0x2a0d8:return 'presentation: derived object dimensions'
  if 0x2a0fa<=off<0x2a418:return 'presentation: pit drawing workspace'
  if 0x2a41a<=off<0x2a62e:return 'presentation: mirror and clipping workspace'
 return 'UNCLASSIFIED'

writes=[]
for pc,i in sorted(seen.items()):
 op=i.mnemonic.split('.')[0]
 if op in ('lea','pea','jsr','jmp','link','unlk','tst','btst','muls','mulu','divs','divu','chk') or op.startswith('cmp') or not i.operands:continue
 if i.operands[-1].type!=M68K_OP_MEM:continue
 writes.append(dict(pc=label(pc),instruction=i.mnemonic+' '+i.op_str,classification=write_class(pc,i)))
unknown=[w for w in writes if w['classification']=='UNCLASSIFIED']
out=scratch(sys.argv[1])
result=dict(status='CLASSIFIED' if not unresolved and not unknown else 'UNCLASSIFIED',
            game_sha256=digest(Path(GAME).read_bytes()),capstone_version=cs_version(),
            instructions=len(seen),write_instructions=len(writes),
            unresolved=unresolved,unclassified=unknown,writes=writes,
            classes=dict(collections.Counter(w['classification'] for w in writes)),
            note='Includes all 16 colour-kernel entries and four A5 transform targets. Implicit JSR/BSR stack pushes are stack, not game-state stores. Static classification is supplemented by call-boundary dumps and traces, not a physics equivalence test.')
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='writes'},indent=2))
if result['status']!='CLASSIFIED':raise SystemExit(1)
