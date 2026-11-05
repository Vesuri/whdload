# Analogue rev counter display

Current 2.0b (13.10.2026) prevents the analogue needle from wrapping around the
dial when over-revving, in either framerate mode. Display limits match the last
numbered marks in the original dashboard artwork: Porsche 7000, Ferrari 10000,
Lotus 7000, Countach 9000 RPM. The digital Corvette keeps its original path.
Engine RPM, power, over-rev threshold, damage counter and event are unchanged.
The reported trails were the printed red-line marks (confirmed by the user).
No blitter/redraw change is included.

## Cause and implementation

H4:$42A0 originally clamps the analogue lookup to the car's engine-table maximum
(15000), not to the dial's scale. The coordinate tables continue around the dial
and contain only 430 bytes from car-data +$328 to EOF; the old index could even
exceed that data above 13759 RPM. In neutral the Porsche fixture reaches 12600
before its original over-rev event, pointing left again. In gear it reaches
8531 with the needle pointing down. Neither observation depends on a host RAM
write or host input automation.

An always-on overlay patch captures the actual loaded car index at h4:$82A2
(the argument in the car loader's stack frame; the menu-selection variable can
be -1). It stores a private display limit. H4:$42A0 clamps only D0, then performs
the displaced engine-table comparison; the original low clamp and lookup follow.
The highest new byte index is 312 (10000 RPM), within every analogue table.
Both hooks are whole instructions with no direct incoming interior targets.
The guard checks the h4 entry signature and original display-load opcode. Every
fresh overlay gets patched before the existing cache flush. Already-patched
loads are skipped. C2-off retains original gameplay plus this display fix.

## Reproduction and evidence

`tools/rpm_capture.py NAME CAR C2` builds an ignored scratch VERIFY fixture and
starts a separate A1200/68040 session. It engages first gear and holds throttle;
`RPM_NEUTRAL=1` holds throttle without engaging a gear. The fixture changes only
the guest input tape. This intentionally invalidates the historical tape unit
vectors, so these captures are not used to claim the normal VERIFY suite passes.
Slaves, scratch source, data samples, configuration and screenshots are retained
under `tmp/rpm-needle/`; exact source and slave hashes are in each metadata file.
No live user game is stopped or changed. The native debugger reads memory and
advances emulated fields; all emulator cleanup is scoped to the verified PID.

`before-porsche-on` and `neutral-porsche-on` reproduce the original display.
`wait-porsche-on` is a rejected diagnostic: adding graphics.WaitBlit produced
pixel-identical matched screenshots. No wait is present in the final code.
The fixed `final-*` captures cover neutral over-rev for all five cars and in-gear
Porsche, including Ferrari with C2 off. Dashboard screenshots are inspected
against original ILBM artwork. Fixed and baseline Porsche samples are compared
for RPM, speed, gear, counter and over-rev event timing.

`tools/rpm_units.py` builds a separate guest-side exhaustive runner calling the
production helpers for all 65536 signed-word inputs and five loaded car choices:
327680 cases, zero failures. It checks result, preserved upper D0 word, original
RPM memory, and the downstream signed comparison. `units-run` also retains the
unmodified normal VERIFY assertions. `tools/rpm_smoke.py` runs copied release
slaves through startup, 1000-field attract driving and native quit, with C2 off
and on. `audit.json` covers all 84 declared ranges. Final acceptance and hashes
are in `acceptance.json`; all checks pass.

Initial `fixed-neutral-*` attempts stopped at the capture tool's Latin-1 listing
reader error and were cleaned up; they are not accepted captures. They remain as
diagnostic evidence. Real hardware tests remain deferred; NTSC is unvalidated.
The current release remains local and the historical overlay-cache A/B pair is
unchanged.
