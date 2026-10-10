#!/usr/bin/env python3
"""Read VERIFY-only cache policy and actual startup CPU control registers."""
import argparse
import json
from pathlib import Path
import struct
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
p.add_argument('--expect-mmu', choices=('on','off'))
p.add_argument('--expect-caches', choices=('on','off'))
a=p.parse_args()
config_path=a.capture/'configuration.json'
config=json.loads(config_path.read_text()) if config_path.exists() else {}
# The NOMMU emulator model retains TC register writes but does not translate.
emulator_no_mmu=str(config.get('CPU', '')).endswith('-NOMMU')
results={}
for file in ('code.bin','final-code.bin'):
 data=(a.capture/file).read_bytes(); pos=0; found=[]
 while (pos:=data.find(b'PDCACHE1',pos))>=0:
  values=struct.unpack_from('>6I',data,pos+8)
  if values[0]: found.append(values)
  pos+=8
 assert len(found)==1, f'{file}: expected one initialized cache record'
 v=found[0]; result={k:hex(n) for k,n in zip(('initialized','requested','whdload_policy','attnflags','cacr','tc'),v)}
 flags=v[3]; cacr=v[4]; tc=v[5]
 result['translation_control_enabled']=bool(tc & (0x8000 if flags & 8 else 0x80000000))
 result['emulator_mmu_disabled']=emulator_no_mmu
 result['mmu_translation_enabled']=result['translation_control_enabled'] and not emulator_no_mmu
 result['instruction_cache_enabled']=bool(cacr & (0x8000 if flags & 8 else 1))
 result['data_cache_enabled']=bool(cacr & (0x80000000 if flags & 8 else 0x100))
 result['branch_cache_enabled']=bool(flags & 128 and cacr & 0x800000)
 assert not result['branch_cache_enabled'], 'Unsafe 68060 branch cache'
 results[file]=result
assert results['code.bin']==results['final-code.bin'], 'Diagnostic record changed'
base=int((a.capture/'game-base.txt').read_text(),0)
for file in ('chip.bin','final-chip.bin'):
 chip=(a.capture/file).read_bytes()
 pointer,length=struct.unpack_from('>2I',chip,base+0x4944)
 assert length==0, 'Loader did not supply an empty command line'
results['empty_game_arguments']=True
sample=results['code.bin']
if a.expect_mmu:
 assert sample['mmu_translation_enabled']==(a.expect_mmu=='on'), 'Unexpected MMU translation state'
if a.expect_caches:
 for key in ('instruction_cache_enabled','data_cache_enabled'):
  assert sample[key]==(a.expect_caches=='on'), f'Unexpected {key}'
 if a.expect_caches=='on':
  assert sample['whdload_policy']=='0x33d' and sample['mmu_translation_enabled'], 'Caches are not isolated as requested'
print(json.dumps(results,indent=2))
