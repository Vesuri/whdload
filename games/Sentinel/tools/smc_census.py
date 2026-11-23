"""Report self-modifying code from tools/sentinel.py `census` state files.

    python3 tools/smc_census.py STATE...

Lists every executed instruction (base-memory address, and the program offset from BASE
$57FE4) whose bytes the CPU also wrote during the traced fields, merged over the state files.
The trace's chip snapshots hold the game's bytes: keep the state files in tmp/.
"""
import pickle
import sys

BASE = 0x57fe4

ex, wr, fields = {}, set(), 0
for path in sys.argv[1:]:
    st = pickle.load(open(path, 'rb'))
    ex.update(st['exec'])
    wr |= st['write']
    fields += st['fields']
hits = []
for pc, size in sorted(ex.items()):
    written = [a for a in range(pc, pc + size) if a in wr]
    if written:
        hits.append((pc, size, written))
print(f'{fields} fields, {len(ex)} instructions executed, {len(wr)} bytes written, '
      f'{len(hits)} instructions both')
for pc, size, written in hits:
    where = f'program +{pc - BASE:05x}' if pc >= BASE else 'low memory'
    print(f'  {pc:06x} ({where}) size {size}: written bytes {", ".join(f"+{a - pc}" for a in written)}')
