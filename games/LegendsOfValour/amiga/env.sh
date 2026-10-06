#!/usr/bin/env bash
# Source this to put the shared ~/.local Amiga toolchain on PATH.
TC="$HOME/.local"
export PATH="$TC/opt/bin:$TC:$TC/fs-uae:$PATH"
# Prefer restored shared ROMs; retain verified legacy files for ROMs not moved yet.
rom_path() {
  local name=$1 candidate
  for candidate in "$HOME/.local/share/amiga/Kickstarts/$name" \
      "$AMIGA_SHARE/Kickstarts/$name" "$AMIGA_SHARE/Kickstarts/$name"; do
    if [ -f "$candidate" ]; then printf '%s\n' "$candidate"; return; fi
  done
  echo "missing Amiga ROM: $name" >&2; return 1
}
export KICKSTART="${KICKSTART:-$(rom_path kick40063.A600)}"
export KICK13="${KICK13:-$(rom_path kick34005.A500)}"
export KICKSTART_A1200="${KICKSTART_A1200:-$(rom_path kick40068.A1200)}"
