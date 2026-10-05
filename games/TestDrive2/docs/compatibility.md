# WHDLoad 20.0 and 68060 compatibility

## Source baseline (2026-10-06, slave 1.6c)

The slave now requires WHDLoad 20.0 and builds against its official public-domain
API headers, KickEmu sources and kick13.asm conventions. The archive SHA-256 and
source identity are in ../whdload/whdload/README.md. Six vendored SDK files match
the official developer package byte for byte. NDK include-name aliases are kept
separately, so KickEmu itself is unmodified.

The old vendored KickEmu was already the 20.0 implementation, with include-name
edits; the shared host API headers and runtime were 19.2. The migration pins the
20.0 headers, uses ws_Version=20 and its ws_MemConfig field, disabled as in the
example (`slv_MemConfig = slv_base`). KickEmu now uses its version-20 expansion
size query. EmulPriv and DMA-safe CACHE settings are retained. No game patch
addresses or simulation/rendering algorithms changed.

Normal and VERIFY builds assemble. A build with WHDLOAD=/nonexistent proves the
old shared headers are not needed. The compiled header declares version 20,
sets EmulPriv and has a zero alternate-memory offset. Audit: 72 hooks, 0 errors.
The packaged installer sources rebuild to the identical normal slave with the
same compiler and NDK. Release archives are generated/re-extracted and checked;
no WHDLoad executable, game data, ROM or capture is committed.

The launcher permits WHDLOAD_BINARY. With no override it prefers the official
20.0 runtime cached in tmp/whd20/official/WHDLoad/C/WHDLoad when present, then
uses the shared installation. Users must supply WHDLoad 20.0 or later. Tests
below explicitly use official 20.0 build 7051 (27.03.2026), leaving the shared
19.2 runtime untouched.

## Startup checks

These are read-only state captures, not frame-rate measurements. All use the
same retained candidate builds in tmp/whd20. The 68060 emulator has A1200 ROM
40.68/chipset, 2 MiB chip + 4 MiB fast memory, no JIT and non-cycle-exact CPU
execution. It is not a recreation of an A4000 accelerator or a real-hardware
validation. The A500 test has 512 KiB chip + 1.5 MiB slow memory.

- A500/68000, VERIFY, CUSTOM2=0 CUSTOM3=1 CUSTOM5=16 (`a500`): reaches the
  race, captures 100 VBL fields; 127/127 assertions, all 76 disabled patch
  ranges retain original instructions.
- 68060-NOMMU, VERIFY, CUSTOM2=0 CUSTOM3=1 CUSTOM5=16 (`060-0`): reaches the
  race, captures 100 fields; 127/127 assertions, all 76 disabled patch ranges
  retain original instructions. Emulator log confirms CPU=68060, MMU=0, JIT=0.
- 68060-NOMMU, VERIFY, CUSTOM2=1 CUSTOM3=1 CUSTOM5=16 (`060-1`): reaches the
  race and captures 100 fields; 127/127 assertions.
- Full 68060/MMU, normal release, CUSTOM2=1 (`060-mmu-normal`): reaches the race
  and captures 100 fields. Log confirms CPU=68060, MMU=68060, JIT=0 and active
  MMU translation (TC=8000, enabled=1). No VERIFY instruments are present.

Both normal and VERIFY startup checks pass in the available configurations.
No FPS measurement or real-hardware validation was made. v2 startup was not
retested for this shared KickEmu/header migration.

## Reported A4000/68060 failure

The user reports that both JOTD's original slave and 1.6b stop at a black screen
on an A4000/68060. Accelerator, ROM, WHDLoad version and MMU configuration are
not yet available; the user is asking for them. No A4000 ROM was found locally.
The 20.0 baseline migration is not a verified fix for this failure.

Next: obtain the report/configuration and determine whether it fails before
KickEmu, before LoadSeg, during intro or on race entry. Compare the original and
new slaves on that configuration, capture the stopped PC/stack and relevant
exception/cache/MMU state, then patch the demonstrated cause. A hardware tester
must confirm the final fix. Do not label generic 68060-emulator success as an
A4000/68060 fix.
