# Phase 6 — complete; hardware A/B deferred

The always-on overlay fix is in normal 1.5b. No further slave change is warranted
by the phase-3 display evidence. The user deferred real A1200/68040 A/B results,
so phase 6 is complete on its local acceptance evidence. Hardware behavior remains
unverified; this is not a hardware pass or release approval.

## Overlay and build checks

The original six-byte MOVEM/RTS exits at root:$06390 and $06916 are replaced by
unconditional jumps. Both helpers flush before the displaced restore/return.
`tools/audit_overlay.py` passes: all five direct incoming branch candidates land
at hook starts, none in their interiors. Indirect targets are not statically proven.
The renewed report is `tmp/phase6/overlay-audit.txt`.

The existing `tmp/build/overlay-smoke.txt` proves both helper hits, flush returns,
restored registers and return stacks on AMIGA_SETUP=a1200-040. Startup, driving
demo and attract-loop evidence remains under tmp/build; no source change required
repeating that smoke. The ReadMe already contains the 1.5b overlay history entry.

Normal SHA-256: ca765222b4257e060e684b80581ed45506d8167c98c016c6d088ad066d6750d4
Baseline SHA-256: 95188df7e59d54ed69d56b0824ab18d461f1a2a5dad01ea58387aba96a0f2b56

Both files are unchanged. The baseline is the unmodified repository-1.4 rebuild,
not an unavailable shipped 1.4. Public archives contain 1.3. Input/archive and
pristine-extraction checks pass. VERIFY instrumentation is absent from this pair.

## Normal quit

`tmp/phase6/quit-040/` retains the exact slave, machine config, screenshots,
commands/responses, native emulator hash, startup sequence and result.json.
The pinned native-input emulator ran PAL A1200/68040, 25 MHz, 2 MiB chip and
8 MiB fast, WHDLoad 20.0, MMU preset enabled and JIT disabled. CACR=$80008000;
the emulator explicitly reports DCACHE_EMULATION=0. No cache-coherency inference
is drawn from this run.

From the game directory:

```sh
FSUAE="$PWD/tmp/phase3/native-emulator/fs-uae" AMIGA_SETUP=a1200-040 WARP=1 \
  SLAVE="$PWD/tmp/build/release/TestDrive.Slave" python3 tools/td.py serve
# Once the game is visibly running, from another shell:
python3 tools/td.py stop
python3 tools/td.py gdb 'monitor key 5d 1'
python3 tools/td.py gdb 'monitor fields 30'
python3 tools/td.py gdb 'monitor key 5d 0'
python3 tools/td.py gdb 'monitor fields 300'
# Inspect a screenshot at a fresh output path, then clean up:
python3 tools/td.py quit
```

The before image shows the Ferrari introduction. Native key press $5D and
release $DD were dequeued, the MMU was disabled during exit, and the after
image shows the AmigaDOS `1>` prompt with no error text. The emulator remained
running until the separate debugger shutdown. This proves the WHDLoad quit-key
path from the introduction, not a full player race on this preset. All controls
used the emulated keyboard queue; no host UI/accessibility input was used.

## Display review

Phase 3 reviewed startup, all five cockpits, crash/recovery, radar ticket and
gas-station/stage transition. No persistent original display defect was found.
The retained recovered-cockpit, after-ticket and settled station images were
rechecked for phase 6. Arbitrary partial-draw screenshots are not defects;
phase-4 right-edge padding lies outside the game rectangle. No affected scanline
was identified, so there is no justified display patch or targeted copper trace.
Coverage remains limited to those observed scenes. Phase-5 rendering-dependent
clutch, geometry and RNG behavior belongs to the planned opt-in simulation work.

## Hardware handoff

`tmp/dist/TestDrive-overlay-cache-AB.zip` contains only the two slaves, README and
checksums. The same individual slaves are under `tmp/dist/overlay-cache-ab/`.
On the real A1200/68040, compare startup, an attract cycle, a player race and
normal keypad-* quit using identical WHDLoad options with caches/MMU enabled.
Record CPU/clock/RAM, WHDLoad version/options and the outcome for each build;
retain a WHDLoad dump on failure. Hardware results are deferred at the user’s request; they do not block phase 6.
