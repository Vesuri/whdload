#!/bin/bash
# Build the harness EEPROM in mame/pristine: boot once without nvram (defaults),
# break the checksum (brake range word $FF4400 := 0x800), then run the game's
# own control set-up (plans/calibrate.lua), which writes a valid EEPROM.
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$here/../../../tmp/arcade" || exit 1
arcade=$(cd "$here/../../../tmp/arcade" && pwd)
work="$arcade/mame/make-pristine"
rm -rf "$work"; mkdir -p "$work/defaults" "$work/calibrate/nvram/harddriv" || exit 1
printf 'return { events = { {t=20, exit=true} } }\n' >"$work/defaults.lua"
HD_PLAN="$work/defaults.lua" "$here/run.sh" "$work/defaults" "$here/hd.lua" 120 -seconds_to_run 30 || exit 1
cp -p "$work/defaults/nvram/harddriv/"* "$work/calibrate/nvram/harddriv/" || exit 1
python3 -I -c '
import sys
d=sys.argv[1]
for n,v in (("mainpcb_200e",0x08),("mainpcb_210e",0x00)):
    b=bytearray(open(d+"/"+n,"rb").read()); b[0x200]=v; open(d+"/"+n,"wb").write(b)
' "$work/calibrate/nvram/harddriv" || exit 1
HD_PLAN="$here/plans/calibrate.lua" "$here/run.sh" "$work/calibrate" "$here/hd.lua" 120 -seconds_to_run 60 || exit 1
mkdir -p "$arcade/mame/pristine" && cp -p "$work/calibrate/nvram/harddriv/"* "$arcade/mame/pristine/"
