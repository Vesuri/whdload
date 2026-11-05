from pathlib import Path
import struct,json,collections,hashlib
root=Path('tmp/d-original-hunk');b=(root/'main.hunk').read_bytes();u=lambda off:struct.unpack_from('>I',b,off)[0]
assert [u(i) for i in range(0,32,4)]==[0x3f3,0,1,0,0,0xf0fb,0x3e9,0xf0fb]
size=u(28)*4;code=b[32:32+size];off=32+size
assert u(off)==0x3ec;count=u(off+4);assert u(off+8)==0
refs=list(struct.unpack_from('>'+str(count)+'I',b,off+12));end=off+12+count*4
assert u(end)==0 and u(end+4)==0x3f2 and end+8==len(b)
assert len(set(refs))==len(refs) and all(a%2==0 and a+4<=size for a in refs)
values={a:int.from_bytes(code[a:a+4],'big') for a in refs}
print("external/end targets",[(hex(a),hex(v)) for a,v in values.items() if v>=size])
assert all(v<=size for v in values.values())
(root/'main-unrelocated.bin').write_bytes(code)
report=dict(size=size,relocations=count,sha256=hashlib.sha256(b).hexdigest(),relocations_by_source_4k=dict(sorted(collections.Counter(hex(a&~4095) for a in refs).items())),relocations_by_target_4k=dict(sorted(collections.Counter(hex(a&~4095) for a in values.values()).items())),references=[dict(offset=hex(a),target=hex(v)) for a,v in sorted(values.items())])
(root/'relocations.json').write_text(json.dumps(report,indent=2)+'\n');print('code/data',hex(size),'typed relocations',count,'target range',hex(min(values.values())),hex(max(values.values())))
