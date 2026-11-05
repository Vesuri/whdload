from pathlib import Path
import json,struct,bisect
r=Path(__file__).resolve().parents[1]
class Addresses:
 def __init__(self,memory,table):
  self.table=table
  self.rows=[]
  for g in json.loads((r/'tmp/manifest/step2-overlays.json').read_text())['groups']:
   for h in g['hunks']:
    if h['number']<=208:
     actual=struct.unpack_from('>I',memory,table+h['number']*4)[0]*4+4
     if actual==4 and h['number']>=206:continue # optional stub overlay not loaded yet
     assert 8<actual and actual+h['size']<=len(memory),(h['number'],hex(actual))
     self.rows.append(dict(hunk=h['number'],old=h['base'],actual=actual,size=h['size']))
  self.by_old=sorted(self.rows,key=lambda x:x['old']);self.by_actual=sorted(self.rows,key=lambda x:x['actual'])
  self.old_keys=[x['old'] for x in self.by_old];self.actual_keys=[x['actual'] for x in self.by_actual]
 def map(self,value,reverse=False):
  rows=self.by_actual if reverse else self.by_old;keys=self.actual_keys if reverse else self.old_keys;k=bisect.bisect_right(keys,value)-1
  if k<0:return value
  x=rows[k];src=x['actual'] if reverse else x['old'];dst=x['old'] if reverse else x['actual']
  return dst+value-src if value<src+x['size'] else value
 def canonical_memory(self,memory):
  self.__init__(memory,self.table) # optional stubs load after race entry
  result=bytearray(memory[:0x80000])
  for x in self.rows:result[x['old']:x['old']+x['size']]=memory[x['actual']:x['actual']+x['size']]
  exact_bases={x['actual']:x['old'] for x in self.rows}
  # Include native DOS allocation/link headers at their canonical identities.
  for x in self.rows:
   result[x['old']-8:x['old']]=memory[x['actual']-8:x['actual']]
   link=struct.unpack_from('>I',result,x['old']-4)[0]
   if link:struct.pack_into('>I',result,x['old']-4,(exact_bases.get(link*4+4,self.map(link*4+4,True))-4)//4)
  # HUNK_RELOC32 explicitly identifies native pointer fields, including tables.
  from overlay_map import catalog
  by_hunk={x['hunk']:x for x in self.rows}
  for g in catalog():
   if g['header'] not in (0,0x22f30,0x30a30,0x30a7c):continue
   for h in g['hunks']:
    if h['number'] not in by_hunk:continue
    for offsets in h['reloc'].values():
     for off in offsets:
      at=by_hunk[h['number']]['old']+off
      value=struct.unpack_from('>I',result,at)[0]
      struct.pack_into('>I',result,at,self.map(value,True))
  for at in (0x24fd0,0x24fd4):struct.pack_into('>I',result,at,self.map(struct.unpack_from('>I',result,at)[0],True))
  return result
 def normalize_trace(self,path):
  from amigaxdev import barto
  t=barto.load(path);raw=bytearray(path.read_bytes());changed=0
  for f in t.fields:
   off=f.insn_off
   while off<f.insn_end:
    while True:
     value=struct.unpack_from('<I',raw,off)[0]
     if value>=0xffff0000:off+=4;break
     new=self.map(value,True)
     if new!=value:struct.pack_into('<I',raw,off,new);changed+=1
     off+=4
    off+=68
   assert off==f.insn_end
  path.rename(path.with_name('detail-raw.bin'));path.write_bytes(raw)
  return dict(changed_pc_words=changed,scope='Only native PC/call-stack address words normalized; registers, cycles and all other trace bytes unchanged')
