#!/bin/bash
# tools/play_check.sh [run options]: the gameplay route (docs/development.md#the-play-check).
# Boots with ENTRY=1, takes tools/sentinel.py's route into landscape 0000 and plays it through
# the emulator's keyboard and mouse: a boulder on a visible square, a robot on it, absorbing
# the robot and making it again, transfer, U-turn, hyperspace, a hyperspace with too little
# energy (the player dies and the landscape restarts), ESC to the title and back in, and F10. Each step
# waits a bounded number of fields for its own record in the game's state (energy $1784, the
# player's object $1685, headings $77C0+object, the displayed picture, WHDLoad's exit) and
# fails if it does not come. On the way it checks the sound module's patch: the bytes in
# place and the effect trigger's DMA-off wait at least 12 raster lines long.
# Run options are common/run.sh's (SETUP=a1200-040 WHD_ARGS=DCACHE INSTANCE=b ...).
set -u
cd "$(dirname "$0")/.."
. ../../common/env.sh
export WARP=1 WINDOW=none DETERMINISTIC=1 JOY0=none ENTRY=1 VERIFY_EXIT=1 "$@"
export INSTANCE=${INSTANCE:-play}   # never the default instance: that is the user's make run
inst=$INSTANCE
out=tmp/play_check/${SETUP:-a500}-$inst; rm -rf "$out"; mkdir -p "$out"
exitfile=tmp/run/$inst/.run/dh0/whdload-exit.txt
rm -f "$exitfile"
ENERGY=0x1784 PLAYER=0x1685 HEADINGS=0x77c0
steps=0
t() { python3 tools/sentinel.py "$@"; }
fail() {
  echo "play check: ${SETUP:-a500} ${WHD_ARGS-} FAILED at $1: $2"
  t shot "$PWD/$out/fail.png" > /dev/null 2>&1; t quit > /dev/null 2>&1; exit 1
}
# ok NAME RESULT: a step's record arrived (waitfor's "at N", brk's "hit")
ok() {
  case "$2" in at*|hit*) steps=$((steps + 1)); echo "$1: $2" >> "$out/steps.txt";; *) fail "$1" "$2";; esac
}
# expect NAME ADDR HEX MAX: the bytes at ADDR become HEX (or leave it, !HEX) within MAX fields
expect() { ok "$1" "$(t waitfor "$2" "$3" "$4")"; }
# after an action the view is redrawn, and the game ignores keys until it is done: settle
# for longer than a whole view takes on the a500 (about 120 fields)
settle() { t fields 200 > /dev/null; }
hx() { printf '%02x' $(($1 & 255)); }
line() { local b; b=$(t peek 0xdff004 4); echo $(( ((0x${b:0:4} & 1) << 8) | 0x${b:4:2} )); }

t serve > "$out/serve.log" 2>&1 & spid=$!
for i in $(seq 1 600); do t peek 0x58c6e 2 >/dev/null 2>&1 && break; kill -0 $spid 2>/dev/null || break; sleep 0.5; done
t route > /dev/null || fail route "no server"
t fields 300 > /dev/null
expect "landscape 0000: energy 10" $ENERGY 0a 0
expect "landscape 0000: the player is object 3e" $PLAYER 3e 0
view=$(t front); echo "first view $view" >> "$out/steps.txt"

# pointer mode, aim at the visible square in front
t click > /dev/null; t fields 10 > /dev/null; t pointer 1984 272 > /dev/null
p=$(t peek 0x20f2e 8)
case $p in 4eb9????????4e71) ok "sound module patched" "at 0 ($p)";; *) fail "sound module patched" "$p";; esac

t key 35 > /dev/null                                   # B: boulder, 2 energy
ok "boulder: effect trigger" "$(t brk 0x20f2e 30)"; l0=$(line)
ok "boulder: effect wait done" "$(t brk 0x20f36 5)"; l1=$(line)
lines=$(( (l1 - l0 + 313) % 313 ))
[ $lines -ge 12 ] || fail "effect DMA-off wait" "$lines lines"
ok "effect DMA-off wait $lines lines" "at 0"
expect "boulder: energy 8" $ENERGY 08 300
settle
t pointer 1984 352 > /dev/null; t key 13 > /dev/null   # R: robot on the boulder, 3
expect "robot: energy 5" $ENERGY 05 300
settle
# the game absorbs only what stands on a square the player sees: here the boulder's top
t pointer 1984 600 > /dev/null; t key 20 > /dev/null   # A: absorb the robot, 3 back
expect "absorb the robot: energy 8" $ENERGY 08 300
settle
t pointer 1984 352 > /dev/null; t key 13 > /dev/null
expect "robot again: energy 5" $ENERGY 05 300
settle
t key 10 > /dev/null                                   # Q: transfer into it
expect "transfer: the player leaves object 3e" $PLAYER '!3e' 300
settle
obj=$(t peek $PLAYER 1)
h=$(t peek $(printf '0x%x' $((HEADINGS + 0x$obj))) 1)
t key 16 > /dev/null                                   # U: U-turn
expect "U-turn: object $obj turns from $h by 128" $(printf '0x%x' $((HEADINGS + 0x$obj))) $(hx $((0x$h + 128))) 300
settle
t key 25 > /dev/null                                   # H: hyperspace, 3
expect "hyperspace: energy 2" $ENERGY 02 600
expect "hyperspace: the player leaves object $obj" $PLAYER "!$obj" 0
settle
t key 25 > /dev/null                                   # under 3: the player dies
expect "hyperspace with 2: the player dies" $PLAYER 00 1500
expect "the landscape restarts: energy 10" $ENERGY 0a 1500
expect "the landscape restarts: object 3e" $PLAYER 3e 0
settle
t fields 100 > /dev/null; t key 44 > /dev/null; t fields 400 > /dev/null
v=$(t front); [ "$v" = "$view" ] || fail "re-entry draws the first view" "$v, not $view"
ok "re-entry draws the first view" "at 0 ($v)"
t key 45 > /dev/null                                   # ESC: to the title
expect "ESC: out of the landscape" $PLAYER 00 400
t route > /dev/null; t fields 300 > /dev/null
expect "title to landscape 0000: energy 10" $ENERGY 0a 0
v=$(t front); [ "$v" = "$view" ] || fail "title to the first view" "$v, not $view"
ok "title to the first view" "at 0 ($v)"
t key 59 > /dev/null                                   # F10: WHDLoad quits
for i in $(seq 1 20); do [ -s "$exitfile" ] && break; t fields 50 > /dev/null; done
r=$(tr -d '\r\n ' < "$exitfile" 2>/dev/null)
[ "$r" = OK ] || fail "F10 quits WHDLoad" "${r:-no whdload-exit.txt}"
ok "F10 quits WHDLoad: $r" "at 0"
t quit > /dev/null
echo "play check: ${SETUP:-a500} ${WHD_ARGS-} passes ($steps steps)"
