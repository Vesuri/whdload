# Ferrari Formula One performance build

Build the single slave from `Games/FerrariFormulaOne_WHD.s` with:

```
python3 Games/FerrariFormulaOne/build.py --game /path/to/data/racemenu --out /path/to/build
```

The build needs vasm (`VASM`), WHDLoad includes/sources (`WHDLOAD`), NDK includes
(`NDK`), Python capstone and amitools. Output and game data must remain outside
tracked source. The build reads SPS 0481's relocation records; it does not copy
game data into the distribution. `layout.json` identifies canonical hunk
addresses used in the audited assembly. Every live game address is bound through
the game's current hunk table, including reloads. Build offsets are not game
addresses and must never receive native relocation bindings.

`CUSTOM2=0` (the default) selects the original loop. `CUSTOM1` retains its
original meaning there: disable the original slave's timing repair.
`CUSTOM2=1` enables elapsed-time scheduling for SPS 0481 in PAL mode; it supersedes that
repair, so both CUSTOM1 settings select the same performance behavior:

| Machine | Simulation interval |
| --- | --- |
| 68000, with or without Fast memory | Converted 200 ms |
| 68020+, no qualified Fast memory | Native 100 ms |
| 68020+ with qualified Fast memory | Player 20 ms; opponents native 100 ms |

Selection uses WHDLoad's CPU flags and expansion allocation, followed by actual
CPU-hunk and stack placement checks for the fine path. CPU allocations use
MEMF_PUBLIC; DMA resources retain Chip placement. An overloaded A500 retains its
200 ms scheduler and pending time. There is no performance-triggered return to
the legacy loop. Irek's version retains its original path even with CUSTOM2 set.

The combined slave reserves 768 KiB through WHDLoad (256 KiB Kickstart image plus
512 KiB public pool), in addition to 512 KiB Chip memory and host/slave overhead.
This reservation also applies with CUSTOM2 disabled: identical minimum memory
requirements to the small v1.01 release are not claimed. The documented A500
emulator configuration has 512 KiB Chip plus 1.5 MiB Slow memory; the Fast variant
also has 2 MiB Fast. The 020 configurations have 2 MiB Chip, with/without 4 MiB Fast.
These configurations are qualified with WHDLoad 20.1; A500 with 512 KiB Chip
and 2 MiB Fast also passes without Slow memory. Smaller configurations and
WHDLoad 17.0 allocation limits are documented in RELEASE_QUALIFICATION.md.

The elapsed clock is PAL-calibrated. Enabled SPS mode requires WHDLoad to report
PAL; NTSC is rejected with the normal WHDLoad PAL requirement message. The
disabled path and Irek's original path retain their existing video behavior.
Allocation or invariant failures in enabled mode exit WHDLoad with an error;
production never enters a diagnostic halt loop.

Production starts on entry to driving and contains no pinned RNG seed, delayed
demo activation, VERIFY tape or forced-workload fixture. Payloads are assembled
separately to retain 68000-safe instructions on both A500 profiles. The build
selects the accepted R3g arithmetic branches explicitly and verifies all binding
operands after its final assembly pass. Original diagnostic builders remain in
the ignored local development harness.

Integration acceptance passed on 2026-10-14 for SPS 0481 PAL on the four documented emulator
profiles. Controlled exact-state comparisons, 30 exact frames per engine,
CUSTOM2=0 legacy comparisons, 60-second clocks, enabled CUSTOM1 options,
pause/menu/re-entry, failure routes and reproducible builds pass. Fine-path
cycle/debt and DMA audits pass. The current untraced 300-presentation figures
are 4.56 / 4.75 / 6.65 / 13.30 FPS for A500 / A500+Fast / chip-only 020 / 020+Fast;
all 60-second clock errors are below 0.23%. These are current demo measurements,
not matched speedup claims against the original release.

Fine simulation averages 53,747.8 cycles/update; worst rolling five is 58,122.2,
against the 145,600 gate. Peak is 141,613 against 283,750. The matched reference
averages 51,744.7: integration costs about 3.9%, with substantial capacity margin.
Actual tow restores all 503 coarse / 902 fine patch words before native cleanup; pause and
menu/session time do not enter driving debt. Full local evidence is indexed by
`tmp/dev/manifest/production-integration.json` and `tmp/dev/docs/STEP5_CAPACITY.md`.

The accepted 260,292-byte build has SHA256
`60123fd26a8c188925c2213118f417e233ad0f883224372e87feeda477e2a836`.
An independent build from the committed sources reproduces it exactly.

This is an unreleased, opt-in emulator-qualified candidate. The 030/040/060,
cache/MMU, original-option/reload, broader native control/track, save/load and
clock checks are complete in [RELEASE_QUALIFICATION.md](RELEASE_QUALIFICATION.md).
Accelerated profiles present about 16.64 FPS with less than 0.041% clock error in
the measured automatic demo. Those are emulator observations, not physical CPU
rankings. The original-loop observations are reported separately.

For the qualified emulator save/load route, use `NoWriteCache`. Chip-only 020
with WHDLoad 20.1 also needs `ConfigDelay=0` and `SplashDelay=0`. The slave keeps
API 17; WHDLoad 17.0 is functionally qualified with Fast memory, not the tested
Chip/Slow-only arrangements. Use the shared `~/.local/share/amiga/WHDLoad`
installation for development. The local candidate package and hash manifest
remain ignored under `tmp/dev/`; nothing is published.

Human playtesting and real Amiga hardware testing are deferred. Irek is
unavailable and retains its original route. Enabled NTSC is rejected. C4-T01
micro targets remain documented shortfalls; the user-selected C4 matched-
workload no-regression gate has passed. There is no A500 performance fallback.

A local Retroplay-based preinstalled candidate is also available at
`tmp/dev/dist/FerrariFormulaOne_v1.02-rc1_0481_Performance.lha`.
All 40 original game-data files, the manual and icon artwork are preserved.
The normal FerrariFormulaOne icon keeps CUSTOM2=0; the added Performance icon
selects CUSTOM2=1. Both carry NoWriteCache and disabled splash delays. The
updated ReadMe includes the original text as historical documentation, with
current memory requirements and qualification limits above it. New icons use
automatic placement. The 53-member level-1 LH5 archive passes CRC testing and
complete extraction/content comparison; its inventory and hashes are recorded
in `tmp/dev/manifest/preinstalled-rc1.json`. Game data and packaging tools remain
ignored and local; this archive is not published.
