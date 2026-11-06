# Step 6: tfx.020 symbol and patch map

Complete. All offsets below refer to the pristine tfx.020 code hunk, except
explicit beta hunk/offset pairs and external slave/asset regions. Evidence is in
`tmp/step6/`; no executable, slave, FPSP or emulator code changed. This is a static
identity/porting audit of the step 5 flight, not a new performance measurement.

## What is covered

- `hot-map.json`: all 30 step 5 regions at or above 0.5%, including 28 game entries,
  the slave screen copy and loaded image code. Original names are recovered where
  supported; five unnamed game helpers have explicit local labels. The masked
  sprite loop has a local interior label rather than an invented original export.
- `exact-symbol-spans.json`: 723 unique complete beta symbol spans match after
  masking only four-byte fields explicitly present in the original relocation
  tables. Every masked field must also be a relocation in the target. These are
  symbol spans, which can include internal labels or data, **not 723 proved function
  bodies**. Relocation destination values are not themselves an equivalence proof.
- `patch-map.json`: every active address-bearing row of `pl_020` (53) and
  `pl_020_060` (7), including repeated option branches: 60 rows, 57 unique plain
  addresses. Includes hooks inside routines, replacement entries, branch targets
  and data pointers. Existing 1997 counterparts are checked against `pl_fpu_new`
  and `pl_fpu_new_060`; missing ports have reviewed logical counterparts.
- `fpu-map.json`: all six observed F-line sites mapped to exact-span library
  wrappers. These supply the step 9 interception candidates.
- `symbols.csv`: 768 labels for inspection. Unlike the hot map it also includes
  data and interior symbols. Do not blindly create a function at every label.
- `ghidra-audit.txt`: independent 68020/68881 decode at 37 selected entries,
  6,118 instructions, using shared `ExportAuditListing` and `DumpCallGraph`.
  `@` names become `at_` in Ghidra to distinguish them from `_` C wrappers.

The 114 absolute operands in `reloc_2_0_020` are a separate data-placement recipe,
not another routine replacement list. Step 8 must rebuild that recipe from the
merged hunk's actual relocation graph; copying its operand offsets is invalid.
This audit does not claim all 3,332 beta symbols were transferred or all relocation
operands ported. No new patch is authorized solely by a symbol name.

## Matching and evidence

`map_symbols.py` extracts pristine hunks, symbols and relocation tables. It finds
bidirectionally unique 12-instruction anchors and extends matching blocks. Numeric
operand normalization is **candidate discovery only**. `candidate-symbols.json`
(1,028 candidates) and `block-maps.json` remain separate from accepted evidence.
One short normalized match incorrectly identified beta `@LoadTexture` at target
`$4e9fc`: it is excluded from the accepted span map. Nearest-symbol guesses are
never used as recovered function names.

`validate_symbol_spans.py` searches the entire target for unique full-span matches,
keeping nonrelocation bytes exact. This also fixes linear-disassembly omissions:
a zero padding word can consume the first word of a real function, as happened
with `Polygon` and `MakeScanTable`. Decode again from a known entry, not from the
preceding arbitrary word.

Changed compiler output needs semantic review. Reviewed identities preserve
specific operations, global offsets, caller relationships and return behavior:
`@AltFadeColsMiss` skips RGB magenta ff/00/ff and interpolates all three channels
with a divisor of 50; `@MatrixAngleZ` computes the matrix determinant term using
word offsets 0/4/6/12/16 before the arctangent helper; `@SquareRoot` retains the
restoring square-root loop seeded with $40000000. Register allocation and stack
layout differ. The SuperShape dispatcher retains handle decoding, table lookup
and the same global state. Detailed per-entry notes are in `hot-map.json`.

Ghidra is an independent decoder and boundary aid, not the authority for computed
jumps. For example, its `ScanFillDown` function initially ends at $6c51f, while the
matched symbol span covers the generated/dispatch loop area through $6cc88.
`SetColor` itself is only $5765e..$5766e; the step 5 5.73% interval extends to
$5a22c and includes other shape commands. `Polygon` spans internal symbols and
runs to $60df6. The report retains both the original profile interval and the
symbol spans inside it. Do not relabel a whole profiling interval as a single
function's self cost, or treat a span endpoint as a safe overwrite boundary.

## Porting findings

The step 7 sort hooks are $5efbe (32 bytes) and $5f03e (14 bytes). Their original
instruction sequences are byte-identical to the integer sites. `_obcount` is
$5bf10, the last object index is $5bf12, `_depth` is $5bf16, and the parallel index
array is $5c1ce: 348 words (696 bytes) apart. The existing sort replacement still
needs its maximum-object failure reproduced and its replacement verified.

The duplicate-fire hook is $4e080. Its original instruction copies a keyboard
state byte; the equivalent BRA +$24 reaches $4e0a6, bypassing synthesis after the
joystick state has already been set. Step 7 must reproduce the double launch and
check actual launches, not just input bits.

The rendering ports need adapters. Plain `@GouraudFill` at $6b8e0 corresponds to
1997 `GouraudFill` at $4f840, but the former receives y/table on its A6 frame and
the latter receives the scan stream at SP+4 and y through A5. `_TextureFill` is
$4f9f8, reached by `TextureFill` at $4f9e4; its C implementation and stack layout
changed. `ScanFillDown` is $6c4f2. `_texture_ptr` is the geometry pointer cell at
$55bec (beta hunk 6:$80), not the texture pixel data.

The frame limit changed from an immediate inside CMPI to MOVEQ #2,D0 at $1abfe,
followed by CMP D0,D1 at $1ac00. Delta time is now A4-$ba4, rather than A4+500.
The update hooks $1830/$1850 read the new global. The model gate at $1ec38 uses
A4-$ba6 and has a different epilogue; copying `skip_model` would corrupt state.
The zoom division at $1fec4 still divides by 30. These are step 10 port candidates,
not ready-to-apply patches. Existing 060 arithmetic hooks are mapped and unchanged.

## Reproduction and checks

Run from the game directory; input paths are resolved through the existing harness:

```
python3 tools/map_symbols.py
python3 tools/validate_symbol_spans.py
python3 tools/build_symbol_map.py
bash tools/audit_symbols_ghidra.sh
python3 tools/check_symbol_map.py
```

Ghidra defaults to the installed Homebrew distribution and JDK 21; override
`GHIDRA_HEADLESS`/`JAVA_HOME` if needed. Its user settings/project/logs stay in
`tmp/step6`. Shared scripts come from `AMIGA_GHIDRA_SCRIPTS`. The wrapper
checks success text because headless Ghidra can return zero after script errors.
The shared call-graph exporter only resolves its supported JSR cases; it is not
an exhaustive BSR/indirect-call graph. Raw instruction records remain available.

`validation.json` checks all 30 hot rows, all 60 patch rows, all 723 accepted spans,
the 37 selected Ghidra entries, six FPSP sites, sort bytes, fire branch landing,
frame-limit opcode/global and Gouraud ABI signatures. Negative controls reject a
changed Project opcode and the known short false symbol match. Input SHA-256s
remain identical. No game execution test is needed for this read-only mapping;
the strict step 5 baseline and its observer-off equality remain authoritative.
Future 040 runs must retain `--uae_fpu_no_unimplemented=true`.

## Hot entry map

Percentages below belong to the original profiling regions, not necessarily the
single function named at their entry. The JSON lists additional symbols within
each interval and distinguishes exact spans, semantic identities and local names.

| Entry | Identity | Region cost | Evidence |
|---|---|---:|---|
| `0x6c4f2` | `ScanFillDown` | 14.826% | exact relocation-masked symbol span |
| `slave:$20b8` | `do_swap_screen / fast-to-chip screen copy` | 12.510% | external source/capture |
| `0x4e53a` | `MaskSprite_CPU_merge` | 8.713% | local descriptive label |
| `0x55e32` | `Project` | 5.954% | exact relocation-masked symbol span |
| `0x5765e` | `SetColor` | 5.729% | exact relocation-masked symbol span |
| `0x3b93a` | `_xSuperShapeView` | 5.292% | reviewed semantic identity |
| `0x60bfc` | `Polygon` | 3.927% | exact relocation-masked symbol span |
| `0x6a4a2` | `_qdiv` | 2.310% | exact relocation-masked symbol span |
| `0x4f54e` | `_DrawSpriteImage` | 2.308% | exact relocation-masked symbol span |
| `0x38236` | `@UseLevel` | 1.754% | reviewed semantic identity |
| `0x4e6b4` | `_DrawMonoImage` | 1.640% | exact relocation-masked symbol span |
| `0x77c8` | `aircraft_list_update_077c8` | 1.576% | local descriptive label |
| `0x62408` | `_xSuperShapeTranslate` | 1.501% | exact relocation-masked symbol span |
| `loaded image:$0` | `planar image drawing code called at game:$3816` | 1.442% | external source/capture |
| `0x5f252` | `GenLeft` | 1.128% | exact relocation-masked symbol span |
| `0x5f1e0` | `GenRight` | 1.107% | exact relocation-masked symbol span |
| `0x4bdca` | `@SquareRoot` | 1.101% | reviewed semantic identity |
| `0x249a` | `@AltFadeColsMiss` | 1.027% | reviewed semantic identity |
| `0xb7c4` | `@gbased_move` | 0.979% | exact relocation-masked symbol span |
| `0x4b774` | `@MatrixAngleZ` | 0.900% | reviewed semantic identity |
| `0x3f51e` | `@EmmGetAddress` | 0.797% | reviewed semantic identity |
| `0x5f124` | `MakeScanTable` | 0.749% | exact relocation-masked symbol span |
| `0x3bc56` | `@SuperShapeCall` | 0.720% | reviewed semantic identity |
| `0x3d032` | `SuperShape_part_3d032` | 0.693% | local descriptive label |
| `0x60b7c` | `ConeCheck` | 0.647% | exact relocation-masked symbol span |
| `0x7d90` | `aircraft_iterator_07d90` | 0.645% | local descriptive label |
| `0x30b04` | `@flight_computer` | 0.617% | reviewed semantic identity |
| `0x39cac` | `viewport_scale_39cac` | 0.610% | local descriptive label |
| `0x62576` | `_SuperShapeAddMobile` | 0.562% | exact relocation-masked symbol span |
| `0x7d54` | `aircraft_iterator_07d54` | 0.532% | local descriptive label |

## Plain TFX patch counterparts

The name column gives the patch purpose/helper or reviewed identity, not always an
original game symbol. `patch-map.json` retains the opcode, original bytes and
per-site ABI warning. Duplicate rows reflect separate options.

| Plain site | tfx.020 counterpart | Purpose | Status |
|---|---|---|---|
| `$44510` | `$45368` | `pre_display_text_or_image` | already present |
| `$44520` | `$45378` | `pre_display_text_or_image` | already present |
| `$410f0` | `$40c44` | `int2_hook_address` | already present |
| `$41504` | `$41054` | `test_fire` | already present |
| `$4cc02` | `$4e7ae` | `fix_smc` | already present |
| `$018a6` | `$019fc` | `do_swap_screen` | already present |
| `$4cb0e` | `$4e6ba` | `$3f3e` | already present |
| `$4ce36` | `$4e9e2` | `$7cfc` | already present |
| `$4ce06` | `$4e9b2` | `$4e96` | already present |
| `$4cb10` | `$4e6bc` | `draw_mono_image_setup` | already present |
| `$4c800` | `$4e3a8` | `4` | already present |
| `$4bed8` | `$4dba0` | `box` | already present |
| `$4bf00` | `$4dbc8` | `box` | already present |
| `$4c138` | `$4de00` | `draw_line_normal` | already present |
| `$6dd04` | `$500dc` | `draw_line_strip` | already present |
| `$6b8e0` | `$4f840` | `GouraudFill` | missing port |
| `$4d6f0` | `$4f9f8` | `_TextureFill` | missing port |
| `$6b0ee` | `$6c4f2` | `ScanFillDown` | missing port |
| `$016b0` | `$017f8` | `start_frame` | already present |
| `$018a6` | `$019fc` | `do_swap_screen` | already present |
| `$42bbe` | `$4385c` | `$42c68` | already present |
| `$33904` | `$2631e` | `$70017001` | already present |
| `$337fa` | `$261f8` | `$70007000` | already present |
| `$46586` | `$47d48` | `find_click_box` | already present |
| `$4b60a` | `$4d2be` | `wait_vsync` | already present |
| `$015ca` | `$016fe` | `enable_vsync_wait` | already present |
| `$3ff92` | `$3f99e` | `@ThreeScreenSwap_ptr` | already present |
| `$4b1b8` | `$4ce00` | `_screen1_ptr` | already present |
| `$4bbd0` | `$4d884` | `_vblank_clock_ptr` | already present |
| `$130ea` | `$14fbe` | `@Control_ptr` | already present |
| `$0072e` | `$0082a` | `@HandleEjection_ptr` | already present |
| `$3463c` | `$271ee` | `@RemoveDeadMissiles_ptr` | already present |
| `$4a992` | `$4c44a` | `_SetPage_ptr` | already present |
| `$4b028` | `$4cc70` | `_SetLogbase_ptr` | already present |
| `$4a9ce` | `$4c486` | `_PalNtsc_ptr` | already present |
| `$a1fb6` | `$79c0e` | `_pal50_ptr` | already present |
| `$6bd04` | `$6a4b8` | `PlotColour_ptr` | already present |
| `$78d64` | `$715fc` | `_logbase_ptr` | already present |
| `$78d68` | `$71600` | `_current_page_ptr` | already present |
| `$76c0a` | `$6f4a2` | `_sprogtab_ptr` | already present |
| `$5ba1c` | `$55bec` | `_texture_ptr` | missing port |
| `$4bbaa` | `$4d85e` | `WaitingForVsync_ptr` | already present |
| `$282b6` | `$1abfe` | `frame_limit` | missing port |
| `$016e8` | `$01830` | `PlayLevel_update_1` | missing port |
| `$01708` | `$01850` | `PlayLevel_update_2` | missing port |
| `$2dbf2` | `$1fec4` | `@InsideZoomOut_divisor` | missing port |
| `$2caa2` | `$1ec38` | `model_update_gate` | missing port |
| `$282b6` | `$1abfe` | `frame_limit` | missing port |
| `$2dbf2` | `$1fec4` | `@InsideZoomOut_divisor` | missing port |
| `$4c4d8` | `$4e080` | `ReadMouse_double_fire` | missing port |
| `$594d6` | `$5efbe` | `_DrawObjects_sort` | missing port |
| `$59556` | `$5f03e` | `AddObject_sort_full` | missing port |
| `$5642e` | `$5bf16` | `_depth` | missing port |
| `$6aea8` | `$6a438` | `_qmul` | already present / 060-specific |
| `$5a672` | `$60002` | `xTranslate` | already present / 060-specific |
| `$619d2` | `$62766` | `_HorizonFadeProj_MulsL4256` | already present / 060-specific |
| `$619f2` | `$62786` | `_HorizonFadeProj_MulsL4253` | already present / 060-specific |
| `$61a26` | `$627ba` | `_HorizonFadeProj_MulsL4253` | already present / 060-specific |
| `$61a02` | `$62796` | `_HorizonFadeProj_DivsL` | already present / 060-specific |
| `$61a36` | `$627ca` | `_HorizonFadeProj_DivsL` | already present / 060-specific |

## Observed FPSP sites

| Site | Wrapper | Entry |
|---|---|---|
| `$50f82` | `@tan` | `$50f7a` |
| `$5169e` | `@sin` | `$51696` |
| `$516b6` | `@cos` | `$516ae` |
| `$517a4` | `@atan2` | `$5173c` |
| `$517f2` | `@atan` | `$517ea` |
| `$5183c` | `@asin` | `$51802` |
