"""Generate explicit hunk bindings from assembled operands and native relocations.
Never infer pointers by scanning arbitrary bytes. Expected instruction fragments
are adjusted from the executable's relocation records, including split words.
"""
from pathlib import Path
import sys,re,json,struct
from capstone import *
from capstone.m68k import *
from overlay_map import catalog
r=Path(__file__).resolve().parents[1];b=Path(sys.argv[1]) if len(sys.argv)>1 else r/'tmp/build/step5-b6-s5/lean';code=(b/'fine.bin').read_bytes();listing=(b/'fine.list').read_text();symbols={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)}
mp=json.loads((r/'manifest/step2-overlays.json').read_text());hunks={h['number']:h for g in mp['groups'] for h in g['hunks']};native=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes();c=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_020);c.detail=True
records={};why={};relocs={}
for g in catalog():
 if g['header'] not in (0,0x22f30,0x30a30,0x30a7c):continue
 for h in g['hunks']:
  for dest,offs in h['reloc'].items():
   for off in offs:relocs[hunks[h['number']]['base']+off]=struct.unpack_from('>I',native,hunks[h['number']]['base']+off)[0]
def hunk(v):
 return next((h for h in hunks.values() if h['base']<=v<h['base']+h['size']),None)
def addword(off,v,shift,reason):
 h=hunk(v);assert h is not None,(hex(off),hex(v),reason)
 item=(h['number']*4,shift,v-h['base'],struct.unpack_from('>H',code,off)[0])
 assert off not in records or records[off]==item,(hex(off),records.get(off),item,reason)
 records[off]=item;why[off]=reason

def addlong(off,v,reason):
 assert code[off:off+4]==struct.pack('>I',v),(off,v,reason)
 addword(off,v,16,reason);addword(off+2,v,0,reason)
def fragment(probe,native_addr,length,reason):
 for at,v in relocs.items():
  for delta,shift in ((0,16),(2,0)):
   if native_addr<=at+delta and at+delta+2<=native_addr+length:
    pos=probe+at+delta-native_addr
    # A prior candidate patch may intentionally have replaced this operand.
    if code[pos:pos+2]!=native[at+delta:at+delta+2]:continue
    addword(pos,v,shift,reason)
for line in listing.splitlines():
 m=re.match(r'00:([0-9A-F]{8})\s+[0-9A-F]+\s+\d+:\s+(.*)',line)
 if not m:continue
 pc=int(m[1],16);src=m[2].strip()
 if 'public_bind' in symbols and pc>=symbols.get('public_bind',len(code)):continue
 if src.startswith(('dc.','ds.','incbin')):continue
 seq=list(c.disasm(code[pc:pc+24],pc,count=1))
 if not seq:continue
 i=seq[0]
 # Split signature immediates: map the referenced native instruction word(s).
 if i.mnemonic in ('cmpi.l','cmpi.w') and len(i.operands)==2 and i.operands[1].address_mode==M68K_AM_ABSOLUTE_DATA_LONG:
  dst=i.operands[1].imm&0xffffffff;size=4 if i.mnemonic.endswith('.l') else 2
  if hunk(dst):fragment(pc+2,dst,size,'signature '+src)
 for op in i.operands:
  if op.type not in (M68K_OP_MEM,M68K_OP_IMM):continue
  if op.type==M68K_OP_MEM and op.address_mode not in (M68K_AM_ABSOLUTE_DATA_LONG,M68K_AM_AREGI_INDEX_BASE_DISP):continue
  if op.type==M68K_OP_MEM and op.address_mode==8 and op.mem.base_reg!=M68K_REG_INVALID:continue
  value=(op.mem.in_disp if op.type==M68K_OP_MEM and op.address_mode==8 else op.imm)&0xffffffff
  if not hunk(value):continue
  # This is a rounding constant, not a pointer. All other immediate candidates
  # were reviewed in step5-b7-binding-audit.json (address tests/site identities).
  if op.type==M68K_OP_IMM and src.startswith('addi.l') and value==0x20000:continue
  if i.mnemonic.startswith('cmpi.') and op.type==M68K_OP_IMM:continue # handled as native fragment
  needle=struct.pack('>I',value);positions=[j for j in range(2,i.size-3,2) if i.bytes[j:j+4]==needle]
  assert positions,(hex(pc),src,hex(value),op.address_mode)
  for j in positions:addlong(pc+j,value,'operand '+src)
# UpdateHooks deliberately encodes displaced native instructions as dc.w.
# Decode only these explicit instruction blocks, never state/signature tables.
for line in listing.splitlines():
 m=re.match(r'00:([0-9A-F]{8})\s+[0-9A-F]+\s+\d+:\s+dc.w\s+(.*)',line)
 if not m:continue
 pc=int(m[1],16)
 if not symbols['velocity_671e6']<=pc<symbols['FF1MultiplyU64_000']:continue
 words=m[2].split(';')[0].strip().split(',')
 assert all(re.fullmatch(r'\$[0-9a-fA-F]+',w.strip()) for w in words),(hex(pc),words)
 raw=b''.join(struct.pack('>H',int(w.strip()[1:],16)) for w in words)
 assert code[pc:pc+len(raw)]==raw
 seq=list(c.disasm(raw,pc));assert sum(i.size for i in seq)==len(raw),(hex(pc),m[2])
 for i in seq:
  for op in i.operands:
   if op.type not in (M68K_OP_MEM,M68K_OP_IMM):continue
   if op.type==M68K_OP_MEM and op.address_mode not in (M68K_AM_ABSOLUTE_DATA_LONG,M68K_AM_AREGI_INDEX_BASE_DISP):continue
   if op.type==M68K_OP_MEM and op.address_mode==8 and op.mem.base_reg!=M68K_REG_INVALID:continue
   value=(op.mem.in_disp if op.type==M68K_OP_MEM and op.address_mode==8 else op.imm)&0xffffffff
   if not hunk(value):continue
   needle=struct.pack('>I',value)
   positions=[j for j in range(2,i.size-3,2) if i.bytes[j:j+4]==needle]
   assert positions,(hex(pc),m[2],value)
   for j in positions:addlong(i.address+j,value,'displaced instruction '+m[2])
data_candidates=[]
fragment(symbols['FF1Track000Signature'],0x6977a,0x112,'lookahead signature')
fragment(symbols['FF1Track000Signature']+0x112,0x67514,0x16,'lookahead caller signature')
fragment(symbols['FF1Trig000Signature'],0x24fe0,64,'trig signature')
fragment(symbols['FF1C4ColourSignature'],0x32d48,0x1c8,'sprite colour signature')
fragment(symbols['FF1C4MulSiteSignature1'],0x6759a,22,'native multiply site 1 signature')
fragment(symbols['FF1C4MulSiteSignature2'],0x6ea2c,12,'native multiply site 2 signature')
fragment(symbols['FF1C4MulSiteSignature3'],0x6cd54,16,'native multiply site 3 signature')
(b/'bindings.json').write_text(json.dumps([dict(offset=k,hunk=v[0]//4,shift=v[1],addend=v[2],expected=v[3],reason=why[k]) for k,v in sorted(records.items())],indent=2)+'\n')
(b/'bindings.bin').write_bytes(b''.join(struct.pack('>IHHIHH',k,*v,0) for k,v in sorted(records.items()))+struct.pack('>I',0xffffffff))
print(len(records),'word bindings;',len(data_candidates),'explicit data candidates require review')
