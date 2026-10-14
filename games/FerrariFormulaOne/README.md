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
`CUSTOM2=1` enables elapsed-time scheduling for SPS 0481; it supersedes that
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
Minimum-memory release qualification is separate.

Production starts on entry to driving and contains no pinned RNG seed, delayed
demo activation, VERIFY tape or forced-workload fixture. Payloads are assembled
separately to retain 68000-safe instructions on both A500 profiles. The build
selects the accepted R3g arithmetic branches explicitly and verifies all binding
operands after its final assembly pass. Original diagnostic builders remain in
the ignored local development harness.

Integration acceptance is in progress. Initial demo activation has been checked
on the four supported emulator profiles; matched-state, disabled-path, elapsed
and lifecycle acceptance must be completed before integration is marked passed.
Broader tracks/gameplay, Irek performance mode, NTSC, real hardware and human
play-testing are separate release qualification. 030/040/060 analysis is deferred.
