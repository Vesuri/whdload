#!/usr/bin/env python3
import hashlib,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((root/'manifest/project.json').read_text())
assert sha(root.parents[1]/m['source'])==m['source_sha256']
count=0
for name,folder in [('game','FerrariFormulaOne_v1.01_0481'),('installer','FerrariFormulaOne')]:
    for rel,want in json.loads((root/f'manifest/{name}.files.json').read_text()).items():
        p=root/'tmp'/name/folder/rel
        assert sha(p)==want,str(p)
        count+=1
for line in (root/'manifest/archives.sha256').read_text().splitlines():
    want,rel=line.split(None,1)
    assert sha(root/rel)==want,rel
print(f'PASS: source, both archives, {count} extracted files')
