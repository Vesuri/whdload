#!/bin/bash
# Private build only. Reuses installed AmigaXDev aprof build dependencies/objects.
set -euo pipefail
cd "$(dirname "$0")/.."
. tools/env.sh
src="$AMIGA_SHARE/fs-uae-aprof-build/fs-uae"
dest="tmp/profiler-fsuae"
[ ! -e "$dest" ] || { echo "Private build already exists: $dest; preserve it and choose a fresh build directory before rebuilding." >&2; exit 1; }
python3 - "$src" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);m=json.loads(Path('tools/040-event-profiler-source.json').read_text())
for n,want in m['source_files'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==want,n
PY
cp -cRp "$src" "$dest"
patch -d "$dest" -p1 < tools/040-event-profiler.patch
patch -d "$dest" -p1 < tools/040-key-input.patch
make -C "$dest" -j4 > tmp/build/profiler-fsuae-build.log 2>&1
python3 - <<'PY'
import hashlib
from pathlib import Path
sha=hashlib.sha256(Path('tmp/profiler-fsuae/fs-uae').read_bytes()).hexdigest()
Path('tmp/build/040-profiler.sha256').write_text(sha+'\n')
print(sha)
PY
