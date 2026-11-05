# Grand Prix Circuit internals

Supported local executable: data/GrandPrixCircuit, 94,708 bytes; SHA-256
fe1dd79f88e0948c8094ab9da529ad28ecf4f364e66d325004f9f2c547901db8.
Aztec C small data: a4 = hunk 1 + $7ffe. CODE $e544 at file $28, DATA $8918 at
file $e5bc, BSS $4; empty HUNK_OVERLAY at file $171e8.

The KickEmu 1.3 slave requests $80000 chip + $80000 expansion; WHDLoad/preload needs more
host memory. Exit key is keypad *. The loader retains its entry register/stack contract,
DOS assignment, song LoadSeg callback, trackdisk emulation and cache flush. Interface 17
adds an empty slv_config; there is deliberately no inactive player-facing performance option.
Size 94708 uses PatchSeg, other sizes retain the original Patch path. VERIFY stores hunk 0
and a v1-match flag after `GPCVERIFY`; it installs no game hooks. Normal builds omit it.

Existing main patches: delay $174 (returns at $182), protection skips $2b90/$4978,
return $b444, success/return $b2f4, null CloseWindow return $e516. On 68010+, SR reads
at $ac2c/$ac96/$ace6/$ad36/$ad82/$af12/$af5e become CCR reads. Song drivers share code:
INTREQ operands $4fe/$a44/$a74 and eleven DMACON hooks are preserved exactly in source.

The overlay manager is h0:$d42c/$d43e; $d4a2 writes JMP opcodes, $d4a6 targets and $d4a8
continuation words. All 139 h1:$0000..$0341 stubs are already direct relocated jumps.
Neither code nor data relocation tables point into the manager. No entries, writes or
hardware watchpoint hits occurred from before game entry through opening/car presentations
and two demos. Table snapshots agree with the pristine relocated bytes. Large-watchpoint
positive controls caught native VBL writes on both the A500 (WHDLoad 19.2) and A1200.
Conclusion for this v1: linked inactive overlay support; no runtime stub rewriting.

The native $772a VBL server updates -31790(a4) and steps every six fields using -29928/-29926.
Simulation lives in the interrupt; drawing lives in the main loop ($7094..$7264). The candidate
swap marker is $39e (LoadView inside $372); no display timing change is made. Static renderer,
physics and timer details are in PERFORMANCE_PLAN.md. They still need Phase 2+
measurement/validation, and have not been changed.

Phase 1 code checks exclude only known native mutable fields: h0:$8..$17 startup,
$b220/$b228 audio state fields and $b6ea native runtime storage. All other bytes, relocated
back to file values, match the original except separately checked JOTD patches. 58,642 bytes
checked on 68000; 58,628 on 68020. Negative code corruptions fail. Actual two demo data
snapshots differ in 1,154 bytes, so the whole-data comparator is not silently ignoring GPC.

Validation scope: shipped/baseline/normal/VERIFY startup and demo on A500; normal on A1200;
WHDLoad 19.2 and 20.0. Pixel-identical active opening screen, intact protection/music hooks,
no unexpected game-code changes. Not a timing/per-field equality claim: KickEmu/BASM
encodings and runtime timing differ. WHDLoad 17, real hardware, other executable versions
and manual full-race play have not been tested. No performance measurements were taken.

## Phase 2 measurements

- Measurement code lives entirely inside `IFD VERIFY` / `verification.s`. `CUSTOM3=1`
  replaces the six-byte VHPOSR read at h0:c12c with `moveq #0,d1; nop; nop`, keeping the
  native RNG otherwise intact. `CUSTOM5=1` replaces the six-byte joystick read at c1de.
  The native field counter drives the tape: accelerate before field 100, up-left 100–105,
  up-right 106–111, accelerate 112–199, brake 200–299, coast 300–399, then accelerate.
  Menus before the first race receive neutral input. Fire/keyboard input is not synthesized. The native attract
  driver remains in control: this establishes capture reproducibility, not handling
  equivalence or coverage of all player controls. Conditional patch commands require
  WHDLoad 17.2+ in VERIFY; these measurements use 20.0.
- The six-byte store at 707a records the native race epoch and replays the original store,
  preserving registers and X. The first loop at 7094 is armed from CPU reset after a
  calibration boot; skip 300 native VBL entries at 772a, then discard the partial current
  field. The 100-field trace covers the start-light transition and initial acceleration;
  the 1,000-field counter continues through the opening driving section. These are fixed
  windows, not whole-race averages. All runs use PAL, `DETERMINISTIC=1`, `CUSTOM2=0`,
  `CUSTOM3=1`, `CUSTOM5=1`, and both joystick devices AND port modes disabled.
- Calibration now requires a live, initialized VERIFY record. A low-quorum byte search
  found a false code address before the 68030 game had loaded; those failed boots are
  excluded. Code/data discovery follows LoadSeg and checks the resident slave's initialized
  resload pointer, excluding PRELOAD/file copies. Each capture retains its exact slave,
  options, RAM, epoch, CACR and emulator logs.
- Two fresh A500 boots match exactly in all 100 instruction/register/cycle records, DMA
  records and active-pixel images, and the entire data hunk at both boundaries. The expanded A1200 pair
  passes the same check. No arbitrary game-state bytes are masked;
  only pointer relocation normalization and the external emulator image border are excluded.
  The 68030 pair matches all 1,000 swap counts AND the complete before/after 4 MB fast RAM.
- Full traces and read-only `SWAP_ONLY` counts agree in every one of the first 100 fields
  on both 68000 and 68EC020. The LoadView site 039e produces exactly one displayed-buffer
  transition on the following field for all 9 A500 and 22 A1200 publications. DMA fetch
  addresses identify exactly two bitplane sets. The counter skips the partial field just
  as the profiler does; starting it at zero instead of -1 would introduce a one-field
  error. This validates publication counting, not correct ownership of the drawing buffer.

| PAL configuration | 1,000-field baseline | Completed intervals / fields | Actual CACR |
| --- | ---: | ---: | --- |
| A500, 68000, 512 KB chip + 1536 KB slow | 5.6402 fps | 111 / 984 | Not present |
| Expanded A1200, 68EC020, 2 MB chip + 4 MB fast | 14.5226 fps | 289 / 995 | $00000000, caches off |
| A1200, 68030/25, 2 MB chip + 4 MB fast | 24.6747 fps | 493 / 999 | $00002000, I/D enable bits clear |

FPS is `50 * completed swap intervals / elapsed fields` between the first and last
publication. The short 100-field trace rates are 4.6512 and 11.4130 fps respectively;
they must not be mixed with the longer baseline. The 68030 uses real CPU speed,
multiplier 0, frequency 25,000,000 and cycle-exact mode, without WHDLoad's MMU option.
Its backend supplies no usable instruction trace, so no CPU-cost figures are claimed.
These are emulator baselines, not hardware measurements; a stock no-fast-RAM A1200 was
not part of this requested matrix. Cache policy is unchanged.

| Cost in the 100-field trace | A500 | Expanded A1200 |
| --- | ---: | ---: |
| Four-plane span-fill region 8864, self | 21.08% | 17.79% |
| Span wrapper 883e, self | 12.90% | 8.67% |
| Shape-blitter region c7f4, self | 8.77% | 16.15% |
| Line drawer cfd2, self | 4.89% | 5.33% |
| Rectangle fill cce2, self | 3.07% | 5.23% |
| Movem clear ce1e, self | 2.47% | 6.56% |
| Draw scene 729a, inclusive | 76.76% | 81.69% |
| Road renderer 818c, inclusive | 44.52% | 51.39% |
| Blitter polling, game + KickEmu | 13.37% | 30.49% |
| Level-3 IRQ entries (VBL / blitter) | 2133 (100 / 2033) | 5156 (100 / 5056) |
| Level-3 inclusive IRQ cost | 12.93% | 7.54% |
| Level-1 entries / cost | 22 / 0.0737% | 21 / 0.0220% |
| Level-4 entries / cost | 13 / 0.0932% | 14 / 0.0226% |
| DMA free / CPU / blitter | 26.19 / 37.53 / 5.95% | 45.19 / 9.88 / 14.59% |
| DMA bitplane / copper / refresh / audio | 28.15 / 0.22 / 1.76 / 0.20% | 28.15 / 0.22 / 1.76 / 0.20% |

No recorded CPU-idle cycles occur. CPU overhead markers account for 0.75% / 0.49% and
are not mislabelled as handler execution. IRQ cost is tracked from vector entry to RTE,
not inferred from stack context. Self ownership uses the nearest known entry; inclusive
ownership follows observed calls. Shared tails and partial calls make these attribution
estimates, not exact function budgets, and inclusive rows overlap. All game regions above
1% self are named, including road rows, object attributes/projection and shape-cache work;
KickEmu waits/clear, Kickstart interrupt/graphics work and WHDLoad interrupt forwarding are
identified separately. Reports retain the call edges and hottest instructions.

- The joystick audit observed all five raw values over 76 reads through field 451,
  each matching the field-indexed schedule. With CUSTOM3=0/CUSTOM5=0 the original
  RNG and joystick bytes are intact; only the VERIFY epoch hook remains.
- The normal slave is byte-identical to the Phase 1 normal build. The final VERIFY slave
  SHA-256 is `00d10fd6d6b01f2499e702bf309fcdfb36181916cdc94b77acfd9aa03ce303ba`.
  The hook audit checks six complete instruction spans, with no direct branch into a
  replaced instruction. Exact live code checks allow only the three named VERIFY sites,
  then check all Phase 1 code/JOTD patches and 139 stubs; a corrupted swap instruction is
  rejected. All 55 pristine game files retain their manifest hashes.
- Local evidence: `tmp/prof/phase2-{a500-full1,a500-full2,a500-aligned,
  a1200-full1,a1200-full2,a1200-swaps,68030-swaps1,68030-swaps2,tape,fixtures-off}`.
  `metadata.json`, `metrics.json`, `profile.txt`, `frames.txt`, `repeatability.txt`,
  `tape.json`, debugger transcripts and retained slaves make the checks reviewable.
  Reproduction commands are in `docs/development.md`; the evidence stays local.
- The user observed blinking horizon/building graphics during this work, consistent with
  the suspected on-screen drawing/buffer-ownership bug. No renderer or swap fix was applied.
  Confirming causality and fixing it remains Phase 5; Phase 3 does not change the renderer.


## Phase 3

The authoritative time/state/rate map and evidence are now in
`GAME_TIME.md`. The VBL period is fixed but starts and
car collisions still couple gameplay to drawing. The displayed PAL clock is slow.
The initialised data payload is $8918, but the allocated data hunk is $9364; include
its BSS tail in state comparisons. Phase 2 repeats were rechecked over the full extent.

Accepted populated-AI step means: 32,305 cycles on A500 and 16,921 on uncached 020.
The proposed periods 6/2 project to 4.01%/3.02% native callback utilization. This does
not prove 50 rendered fps, human handling, native pits or every crash branch. Phase 4
must decide clock/start/collision policy; no performance or gameplay fix is included.
