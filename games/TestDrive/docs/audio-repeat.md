# Opening audio repeat correction

Current 2.0b fixes an inherited Paula stop/start defect, independent of CUSTOM2.
The user reported repeated drum hits on the 68040, especially near the spoken
introduction. Native debugger events reproduce the fault in both unmodified
repository 1.4 and the previous 2.0b release. No guest-memory writes or host input
helpers are used. All outputs and pristine inputs remain under ignored tmp/.

## Cause and correction

The root level-4 audio handler decrements a repeat counter at the initial DMA
interrupt and again at sample completion. One-shots start at 1. On completion,
it mutes the channel, sets period 150, disables DMA and acknowledges the request.
Paula's manual-output state needs a pending request at the end of a word to
return to idle. On a fast CPU, repeated acknowledgements can prevent that state
transition. The next sample can miss its initial DMA interrupt; its first end
interrupt decrements 1 to 0, so the sample plays a second time before stopping.
The emulator source audio.cpp audio_state_channel2 (states 2/3, irqcheck) and the
observed interrupt timings agree. Its DMA-wait workaround also fires on the old
player; the corrected capture no longer needs that workaround.

Four root patches in TestDriveHD.s:

- $2574 (12 bytes): explicit stop disables the channel interrupt before DMA.
- $2684 (10 bytes): completion stop does the same; retains the stop timestamp.
- $26CA (18 bytes): briefly raises IPL while snapshotting and disabling audio
  interrupts, preventing a concurrent level-4 stop from being re-enabled by a
  stale saved mask. Restores SR before returning to the level-3 VBL server.
- $276A (6-byte jump, bypasses tail through $278A): clears stale requests for
  new starts, enables DMA, then restores saved/new interrupts. The game's
  managed-channel mask still excludes looping music/engine channels.

The existing two-VBL stop/start separation, channel state, song data and pitch
are retained. The new tail restores exactly the original saved registers and
returns zero as before. audit_audio.py checks exact original instructions and
external direct branches over the entire bypassed tail. The shared patch audit
and installed-byte checker include all four hooks. Indirect targets are not
statically proven.

## Reproduction and verification

Source tools/env.sh. tools/audio_probe.py NAME SETUP baseline|release|candidate
true|false selects the data-cache override; all runs use WHDLoad CACHE. Candidate
uses tmp/build, release uses tmp/dist/2.0b, baseline uses the retained original 1.4.
AUDIO_FIELDS defaults to 1000 sound VBL ticks; AUDIO_BOOT_FIELDS defaults to 600
boot fields (use 200 for the faster baseline startup). Captures copy their slave,
record effective machine options and hashes, resolve the loaded root excluding
PRELOAD, and log sample starts and active-channel IRQ counts. Fixed-field monitor
stepping ignores breakpoints, so event collection uses normal continue instead.
A 68020 control explicitly has 8 MiB fast RAM for the same dump range.

Accepted evidence in tmp/audio/:

- release040-activeirq and baseline040-early: 11 complete samples each; 1,892
  entries with a negative old repeat count, and missed initial IRQs on drum
  starts at sound fields 67 and 163. The latter runs until field 168, approximately
  twice the 566-byte sample's normal duration at period 357.
- fixed040-activeirq: data-cache-off comparison; all 12 complete samples have
  initial/completion counts [1, 0], with zero negative-count IRQs.
- fixed040-cache-intro: 1,000 sound fields with instruction/data caches enabled;
  all 59 samples complete, exactly [1, 0], no missed initial IRQ or interrupt loop.
  Includes both opening channel-3 samples (13,122 and 50,000 bytes).
- release020-activeirq-3 reproduces the fault on 68020 too. fixed020-activeirq
  has 11 completed samples and one speech sample still playing at capture end;
  initial/completion IRQs are correct and there is no negative-count loop.
- analysis.json in each directory is produced by tools/check_audio.py.

Normal release smoke captures in tmp/corner-jump/audio-fix-{a500,020,040-on,040-off}
reach first attract driving, run 1,000 further fields and quit with native key $5D.
Screenshots confirm driving and the returned AmigaDOS prompt. All installed hook
bytes/options pass check_disabled.py; tmp/audio/installed-hooks.json retains the
results, and combined-audit.json / audit.json retain the branch audits. Both
normal and VERIFY builds pass. Package extraction/rebuild checks are recorded
by package_release.py in the current release manifest.

The user confirms the sample-repeat bug is fixed when listening to release 2.0b
on the a1200-040 emulator with CACHE and enhancements enabled (13.10.2026).
The automated evidence above measures guest playback/interrupts, not host audio
recordings. Real A1200/68040 testing remains deferred.
NTSC remains unvalidated. Failed setup captures and the abandoned full-IRQ probe
are not acceptance evidence. The previous release/package are preserved with
the suffix before-audio-fix. No historical overlay-cache A/B files are changed.
