"""Generate explicit hunk bindings from assembled operands and native relocations.
Never infer pointers by scanning arbitrary bytes. Expected instruction fragments
are adjusted from the executable's relocation records, including split words.
"""
from pathlib import Path
import sys,re,json,struct
from capstone import *
from capstone.m68k import *
from native import catalog
root=Path(__file__).resolve().parent
b=Path(sys.argv[1]); game=Path(sys.argv[2]); kind=sys.argv[3]
code=(b/'fine.bin').read_bytes();listing=(b/'fine.list').read_text()
symbols={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)}
hunks={int(k):dict(v,number=int(k)) for k,v in json.loads((root/'layout.json').read_text()).items()}
native=bytearray(0x80000);relocs={}
for group in catalog(game):
 if group['header'] not in (0,0x22f30,0x30a30,0x30a7c):continue
 for h in group['hunks']:
  base=hunks[h['number']]['base'];native[base:base+len(h['data'])]=h['data']
  for dest,offs in h['reloc'].items():
   for off in offs:
    at=base+off;value=struct.unpack_from('>I',native,at)[0]+hunks[dest]['base']
    struct.pack_into('>I',native,at,value);relocs[at]=value
c=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_020);c.detail=True
records={};why={}
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
 if 'public_bind' in symbols and pc>=symbols['public_bind']:continue
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
  if op.type==M68K_OP_IMM and '#FF1_HOST_' in src:continue # build offsets, never game pointers
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
 if not symbols.get('velocity_671e6',0)<=pc<symbols.get('schedule_install',symbols.get('FF1MultiplyU64_000',0)):continue
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
# NativeExact's explicit signature table (not disassembled as candidate code).
if kind in ('fine','020'):
 p=symbols['FF1NativeSites']
 while True:
  start=struct.unpack_from('>I',code,p)[0]
  if not start:break
  size,tag=struct.unpack_from('>HH',code,p+4)
  addlong(p,start,'native site address');fragment(p+8,start,size,'native site signature');p+=8+size
if kind in ('fine','000'):
 prefix='' if kind=='fine' else '000'
 fragment(symbols['FF1Track'+prefix+'Signature'],0x6977a,0x112,'lookahead signature')
 fragment(symbols['FF1Track'+prefix+'Signature']+0x112,0x67514,0x16,'lookahead caller')
 fragment(symbols['FF1Trig'+prefix+'Signature'],0x24fe0,64,'trig signature')
if kind=='fine':
 fragment(symbols['FF1RenderColourSignature'],0x32d48,0x1c8,'fine colour signature')
if kind=='000':
 fragment(symbols['FF1C4ColourSignature'],0x32d48,0x1c8,'colour signature')
 for label,address,length in [('1',0x6759a,22),('2',0x6ea2c,12),('3',0x6cd54,16)]:
  fragment(symbols['FF1C4MulSiteSignature'+label],address,length,'multiply signature')
# Review explicit address-bearing longword data separately. These are native
# array base and trace site tables; seed/lookup arithmetic constants excluded.
data_candidates=[]
(b/'bindings-data-review.json').write_text(json.dumps(data_candidates,indent=2)+'\n')
(b/'bindings.json').write_text(json.dumps([dict(offset=k,hunk=v[0]//4,shift=v[1],addend=v[2],expected=v[3],reason=why[k]) for k,v in sorted(records.items())],indent=2)+'\n')
# Packed table (FerrariFormulaOne_Bindings.s). Header: hunk count.w, then per used hunk
# slot byte offset.w, previous base.l (the canonical base) and new base.l (runtime work).
# Records: delta.w from the previous record's offset (0 ends), hunk index.b, kind.b
# (0 long, 1 high word, 2 low word), hunk-relative addend.w. A word's expected value is
# derived from the hunk's previous base, so no expected words are stored.
for k,(slot,shift,addend,expected) in records.items():
 assert expected==((hunks[slot//4]['base']+addend)>>shift)&0xffff,(hex(k),slot,shift,addend,expected)
used=sorted({v[0] for v in records.values()});index={s:i for i,s in enumerate(used)}
assert len(used)<256
packed=[];prev=0;items=sorted(records.items());i=0
while i<len(items):
 off,(slot,shift,addend,_)=items[i]
 if shift==16 and i+1<len(items) and items[i+1][0]==off+2 and items[i+1][1][:3]==(slot,0,addend):kind=0;i+=2
 else:kind=1 if shift==16 else 2;i+=1
 delta=off-prev;assert 0<delta<32768 and 0<=addend<65536,(hex(off),delta,addend)
 packed.append(struct.pack('>HBBH',delta,index[slot],kind,addend));prev=off
table=struct.pack('>H',len(used))+b''.join(struct.pack('>HII',s,hunks[s//4]['base'],0) for s in used)+b''.join(packed)+struct.pack('>H',0)
(b/'bindings.bin').write_bytes(table)
print(len(records),'word bindings in',len(packed),'records,',len(table),'bytes;',len(data_candidates),'explicit data candidates require review')
