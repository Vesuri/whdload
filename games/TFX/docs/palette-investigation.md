# Palette investigation (step 12, incomplete)

No yellow glitch has been reproduced, no root cause established and no palette
patch made. The plan's exit check is **not passed**. The initial report describes
a stray yellow colour on the physical A1200/040, without a remembered location,
view, mission, trigger or affected executable. A more specific reproduction or
hardware capture is still needed if the retained emulator routes do not expose it.

## Baseline and observations

The normal slave and both FPSPs rebuilt byte-identically to step 11's baseline;
see `tmp/step12/build-identity.json`. The game/slave sources and shared emulator
are unchanged. All runs use disposable HDFs and native recorded key/mouse input;
there are no guest-code or data fixtures. 040 runs enable unsupported FPU trapping.
020 uses the integer TFX; tfx.020 requires an FPU and cannot be the no-FPU control.
These are diagnostic samples, not a performance comparison or equivalence test.

Evidence is below `tmp/step12/`:

- `survey040`: enrolment, cockpit, F2–F7/F10 view requests, return to F1 and
  settings request. The cockpit and external tracking view are visually verified.
- `survey020`: first survey, with inadequate view-key hold time and an incorrect
  palette-dump address. Keep as failed harness evidence; its palette dumps are invalid.
- `survey020-v2`: 40-field view-key holds and the live relocated palette pointer.
  The screenshots do not prove that every requested external view was reached;
  filenames describe attempted keys. Do not claim a complete 020 view matrix.
- `menus040`, `menus020`: enrolment, save slot, main menu, sampled transitions;
  020 also reaches the arcade menu. A black transition image is not a failure.
- `training040`: training introduction and school image.
- `training040-traced-v2`: longer NOMMU training route reaches aircraft/loadout
  selection. Despite the directory name, its trace files have **no 040 instruction
  records**: this cost-observer backend is unsuitable for full instruction tracing.
- `training040-fulltrace`: validated step-3 MMU backend; 46 sampled fields,
  12,780,514 instruction records. `palette-trace-audit.json` verifies two complete
  SetPal calls, 512 RGB entries and 1,024 colour writes against actual RGB operands
  and palette bank selection. No incorrect write was found in those calls.
- `training020`: extended native training route, including attempted loadout
  confirmation. Later captures contain partially drawn loadout screens; do not
  claim completed mission briefing or exact cross-CPU scene equivalence.
- `training040-traced`: failed output-directory setup before emulator startup.

The nine stable flight palette samples on each CPU match all 256 hardware RGB
entries against the game's live palette snapshot (18 comparisons, 4,608 entries).
No saturated yellow entry (R>200, G>200, B<60) was found in the initial surveyed
fields. This numerical filter is only a search aid: normal artwork can contain
yellow, and other yellow shades or brief faults can escape it. Stable comparisons
and selected screenshots cannot rule out a palette race on physical hardware.
The 040 flight and 020 flight are different executables/cadences; cross-CPU image
or palette byte identity is neither expected nor asserted.

## Code inspection

`static-palette.json` retains disassembly and original-byte correspondence:

- tfx.020 `_SetPal` at $4c32c and `_DiffSetPal` at $4c3ae match the complete symbol
  build spans after relocation masking (130 and 156 bytes).
- They convert 8-bit RGB to AGA high/low nibble writes, select all eight banks
  with BPLCON3 and maintain a CPU-only RGB snapshot. No hardcoded yellow diagnostic
  write was found in these routines. Lack of a visible fault is not proof of safety
  for every raster position or physical machine.
- `_davespal` is used by gameplay palette/fade paths, `_greenpal` by special-view
  handling, and `_colour_override` by UI palette selection. These names alone do
  not establish a development leftover. None was disabled speculatively.
- `_WhitePalette` has an apparently incomplete snapshot-fill loop, but no direct
  reference was found in the decoded target code. It has not been demonstrated
  to cause the reported symptom, and no change was made to it.

## Tools and pitfalls

`tools/step12_survey.py OUTPUT MACHINE` and `tools/step12_menus.py OUTPUT MACHINE`
reuse the accepted cold-boot/hunk locator and enrolment tape. Outputs must be new.
They add observation hooks to the local replay driver's Python source, not to the
game. Native mouse increments and click holds are recorded in `debugger.log`.
The revised menu driver saves its own source; its earlier route variants are
specified by their debugger logs. All tools remain ignored.

For a full 040 dispatch trace, use the step-3 MMU backend and `TRACE_MMU=1`.
The step-9 backend is suitable for palette/DMA screenshots and its separate cost
CSV observer, but does not supply ordinary 040 instruction records. Always count
records before claiming trace evidence. Full dispatch records have no meaningful
instruction costs.

The integer game's palette is moved into the slave's shadow data buffer. Read
its live pointer at code+$4a882; neither the original chip hunk nor merged-hunk
layout is correct. For tfx.020, use code+$4c33a. Version 2 fixes the former mistake.
`step12_report.py` explicitly ignores first-survey 020 palette dumps; null means
not measured. Palette samples are after the captured field, so dynamic/fading
fields are not suitable for this stable-state comparison.

Example from the game directory (substitute a new output directory):

```
FSUAE="$PWD/tmp/step9-emulator/fs-uae/fs-uae" \
  python3 tools/step12_survey.py "$PWD/tmp/step12-new-020" 020
TRACE_MMU=1 FSUAE="$PWD/tmp/step3-emulator/fs-uae/fs-uae" \
  python3 tools/step12_menus.py "$PWD/tmp/step12-new-040" 040
python3 tools/step12_report.py tmp/step12-new-040
```

## Remaining exit work

Identify a visibly wrong yellow frame and its trigger; trace the producer of the
wrong colour, retain a reproducible baseline, then implement the smallest proven
fix. Verify that exact scene on 040 and 020 and the affected 030/060 paths. Do not
mark the step complete based only on normal screenshots or an unrelated latent
palette issue. No new state-mismatch acceptance is implied.

### Follow-up audit

The original report counted 020 records with no resolved PC (None or the
$7fffffff sentinel) as instruction records. The report now separates those
unresolved records and excludes them from instruction evidence. The 020 captures
provide zero usable instruction PCs; their screenshots and hardware RGB samples
remain usable. The 12,780,514 040 full-trace records and two complete SetPal audits
remain valid. This correction does not change any palette comparison or establish
a cause for the yellow report. The raw-key parser was also checked: the recorded
F-key numbers are hexadecimal Amiga raw codes as intended. Input requests alone
still do not prove that every labelled view was reached.

### User follow-up (2026-10-20)

The user could not reproduce the yellow glitch either and suggested that one of
the debug executables may have been running. The affected executable is unknown.
This is an unconfirmed explanation, not evidence that a specific debug build is
faulty or that the current build fixed the symptom. Keep palette code unchanged;
resume diagnosis if an identifiable executable and reproduction become available.
Step 12 remains unreproduced, with its root-cause/fix exit check unmet.
