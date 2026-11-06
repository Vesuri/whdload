#!/usr/bin/env python3
import map_symbols as m,json,re,hashlib
p=m.OUT;hot=json.loads((p/'hot-map.json').read_text());patch=json.loads((p/'patch-map.json').read_text());spans=json.loads((p/'exact-symbol-spans.json').read_text());old=m.load(m.GAME/'TFX.040');new=m.load(m.GAME/'tfx.020')[0];plain=m.load(m.GAME/'TFX')[0]
assert len(hot)==30 and len(patch)==60 and len({x['source'] for x in patch})==57
assert sum(1 for x in hot if x['space']=='game hunk 0')==28
nr={o for v in new['relocs'].values() for o in v}
def valid(s,data):
 h=old[s['beta_hunk']];a=s['beta_offset'];b=s['target'];n=s['size'];rel=[o for v in h['relocs'].values() for o in v if a<=o<a+n];mask={o+k for o in rel for k in range(4)}
 return all(h['data'][a+i]==data[b+i] for i in range(n) if a+i not in mask) and all(b+o-a in nr for o in rel)
assert all(valid(s,new['data']) for s in spans)
# Instruction and data invariants for the next correctness port.
assert new['data'][0x5efbe:0x5efde]==plain['data'][0x594d6:0x594f6]
assert new['data'][0x5f03e:0x5f04c]==plain['data'][0x59556:0x59564]
assert new['data'][0x4e080:0x4e082].hex()=='13f9'
assert new['data'][0x4e0a6:0x4e0ae].hex()=='0839000200dff016'
assert 0x4e080+2+0x24==0x4e0a6
assert new['data'][0x1abfe:0x1ac04].hex()=='7002b24065e8'
assert new['data'][0x1830:0x1836].hex()=='302cf45c48c0'
assert new['data'][0x1850:0x1856].hex()=='302cf45c48c0'
assert 0x5c1ce-0x5bf16==348*2
assert new['data'][0x4f840:0x4f846].hex()=='45ef0004280d'
# Negative controls: changed code must fail; near-match helper must not become accepted symbol.
s=next(x for x in spans if x['name']=='Project');bad=bytearray(new['data']);bad[s['target']]^=1;assert not valid(s,bad)
assert not any(x['name']=='@LoadTexture' and x['target']==0x4e9fc for x in spans)
listing=(p/'ghidra-audit.txt').read_text()
for x in hot:
 if 'target' in x:assert re.search(r'; FUNC .* '+f"{x['target']:08x}"+' - ',listing),x
assert '37 functions, 6118 instructions' in listing
for x in patch:assert x['original_target_bytes']==new['data'][x['target']:x['target']+12].hex()
assert len(json.loads((p/'fpu-map.json').read_text()))==6
manifest={n:hashlib.sha256((m.GAME/n).read_bytes()).hexdigest() for n in ['TFX','TFX.040','tfx.020']}
assert manifest==json.loads((p/'inputs.json').read_text())
(p/'validation.json').write_text(json.dumps(dict(hot_coverage=30,patch_coverage=60,exact_spans_rechecked=len(spans),ghidra_entries=37,sort_byte_equivalence=True,changed_opcode_rejected=True,short_false_match_rejected=True,unchanged_inputs=True),indent=2))
print((p/'validation.json').read_text())
