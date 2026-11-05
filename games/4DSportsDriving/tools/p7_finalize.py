from pathlib import Path
import json,hashlib,struct,gzip
root=Path('tmp/prof/p7-integration');repo=Path('.');src=repo/'src';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
slave=Path('tmp/build/4DSportsDriving.slave');digest=sha(slave);size=slave.stat().st_size
assert digest=='f9ec3a551ade96b648c83ad5266aaae0e431a09321be9f243f8a07a3e6ea0d2a'
criteria=Path('tmp/prof/natural-crest-criteria.json');assert sha(criteria)=='90570d37e39d7fbdf804bbc497959ffe30e60f51bbb60c3e938f041c1d3401db'
assert sha(Path('tmp/prof/native-contact-phase-criteria.json'))=='74afe3d039870269ccf4d160434ec52f05fe195dfb8dc6c338a3aeca613d64ce'
load=lambda p:json.loads(p.read_text())
gate=load(Path('tmp/prof/p7-live/nominal/bridge-handling.json'));assert sum(x['passed']for x in gate['checks'].values())==27 and len(gate['checks'])==29
phase=[]
for n,wanted in [('nominal',53),('minus64',70),('plus64',69)]:
 p=Path('tmp/prof/p7-live')/n;e=load(p/'offline-equivalence.json');assert e['equal_body_records']==795
 c=load(p/'contact-phase-check.json');assert len(c['failures'])==wanted;phase.append(dict(phase=n,exact_records=795,failures=wanted))
native=load(root/'native-state-check.json');assert len(native)==2 and all(x['equal_bytes']==1120 for x in native)
replay=load(root/'replay-check.json');reject=load(root/'reject/abi9-rejection.json');assert reject['loads']==reject['installs']==0
assert '38 disabled optimization ranges match the original' in (root/'legacy.runner.log').read_text()
life=[];fps=[]
for cell,name in [('D','lifecycle-opponent-D2'),('E','lifecycle-opponent-E-short')]:
 p=root/name;v=load(p/'combined-lifecycle.json');f=load(p/'finish-check.json');assert v['outcome']==3 and v['restarted'] and any(x[0]in(1,2,5)for x in v['crash_observations']) and not any(x[1]for x in v['crash_observations']);assert f['overflow']==0 and v['opponent']==1 and v['slave_sha256']==digest
 life.append(dict(cell=cell,emulated_seconds=v['elapsed_fields']/50,shortened_idle=v['diagnostic_short'],crash_restart_finish=True,queue_max=max(v['queue_max'],f['queue_max_at_samples']),overflow=0))
 b=load(root/'fps'/cell/'bench.json');assert b['slave_sha256']==digest and abs(b['steps_per_second']-50)<.25 and b['start']['detail']==b['end']['detail']==0
 fps.append(dict(cell=cell,fps=b['fps'],steps_per_second=b['steps_per_second'],seconds=b['emulated_seconds'],start_tick=b['start']['consumed'],end_tick=b['end']['consumed'],plan_reference=45.29 if cell=='D' else 45.49))
for n in ('save','reload','reject','native-10','native-20','legacy'):
 assert load(root/n/'anchor.json')['slave_sha256']==digest
r=dict(slave_sha256=digest,slave_bytes=size,physics_abi=10,kernels=load(root/'kernel-check.json'),gate_passed=27,gate_total=29,criteria_sha256=sha(criteria),phases=phase,replay=replay,abi9_rejection=reject,native=native,disabled_original_ranges=38,hook_audit='hook-audit.txt',lifecycles=life,fps=fps,experimental=True,excluded={'p7-integration/nominal':'Startup self-tests passed; generic steering route excluded from crest evidence.','lifecycle-D':'No opponent selected; crash not reached.','lifecycle-opponent-D':'Harness missing import, before race.','lifecycle-opponent-E':'180-second watchdog closed the emulator during finish after long idle prelude; compact E run replaces it.'},scope='Exact screened kernels integrated without tuning; accepted experimental27/29, not full handling acceptance. Runtime regression captures use one production SHA. Both frozen criteria unchanged.')
(root/'validation.json').write_text(json.dumps(r,indent=2)+'\n')
plan=f'''## P7. Integrate the screened A4000 correction (complete 2026-10-12)

The user-approved integration is complete. A4000 remains **experimental** and the
unchanged frozen crest gate remains **27/29**, accepted by the 2026-10-12 decision.
Normal and A2500 behavior is unchanged. No landing variant or further tuning was used.

### Production implementation

- Both cars receive the screened endpoint correction after `sim_distance_50`:
  `divmod(3*(Qnew-Qold)+carry,10)`, where `Q=floor(speed*1408/15360)`.
  The remainder at private+32 has floor semantics (0..9), including deceleration.
  Original disassembly confirms `$F11C` saves old speed in car+$2E and no subsequent
  write changes it before `$C326`; new speed is car+$2C. The snapshot layout is unchanged.
- A wheel with zero velocity word and zero velocity fifths uses `sim_release_pair_50`.
  The replay-restored race tick supplies `h5=(2*tick)%5`, with zero meaning5.
  Downward displacement uses the triangular numerators3/7/12/18/25; subsequent
  airborne updates retain the existing2/5 recurrence. Both accelerations and all
  five release ages are covered by executed VERIFY cases.
- A4000 replay physics ABI is10 (file format2). Valid-CRC ABI9 files are rejected
  with the existing invalid-replay message. Native10/20 files remain supported.

Production slave: {size} bytes, SHA256
`{digest}`.
Version remains **2.0b (13.10.2026)**. The local testing archive is rebuilt from
this slave and the updated ReadMe; it is not published.

### Live equivalence and handling

At each start Z(-64/0/+64), all795 body records for ticks6..800 match the frozen
`p7-session1/combined-*.json` rows exactly: XYZ, pitch, speed and four wheel flags.
Nominal live gate results:

| Measurement | Before | Integrated | Frozen limit |
|---|---:|---:|---:|
| Common Y error | 2263 | 1442 | 1247 (fails) |
| Common pitch error | 18 | 11 | 11 (passes) |
| Common speed error | 756 | 7719 | 3400 (fails) |
| Checks passed | 27/29 | 27/29 | 29/29 not claimed |

Phase-family failures (nominal/minus64/plus64) are **53/70/69**, versus70/95/90.
The offline9s Z gap is -39 versus the previous-652, with approach speeds unchanged;
controlled first detections at560/564 reproduce front189/rear105 at580.
These are the accepted partial improvements, not a re-baselined handling gate.
Criteria SHA256 remains
`90570d37e39d7fbdf804bbc497959ffe30e60f51bbb60c3e938f041c1d3401db`;
the phase-family criteria also remain unchanged.

### Regression results

- All4369 physics self-checks pass, including27 new release-age/endpoint cases.
- Native Save Replay followed by fresh-process Load and Play matches all1510
  semantic bytes at1500/1550/1600, including nonzero endpoint remainders, and all1802
  route bytes. Saved file is63912 bytes with valid CRC and ABI10.
- A valid-CRC ABI9 A4000 file is rejected without installation.
- Native10/20 playback each matches the original1120-byte state at tick200.
- `CUSTOM2=0 CUSTOM3=1`: all38 declared disabled ranges match original bytes.
  Hook audit passes1250 relocations and10102 aligned branch candidates.
- Production D/E races select opponent1 through native menus and pass crash,
  restart and finish with zero queue overflow; maximum sampled queue is2.
  D covers196.60 emulated seconds. E covers86.54 seconds with the historical idle
  prelude shortened to remain inside the180-second emulator watchdog. This E run
  is lifecycle coverage, not a two-minute endurance claim.

Ten-second frame-anchored FULL/CUSTOM2=1 measurements, calibrated25/50MHz:

| Cell | Plan FPS reference | Integrated FPS | Simulation steps/s |
|---|---:|---:|---:|
| D / 040/25 | 45.29 | {fps[0]['fps']:.2f} | {fps[0]['steps_per_second']:.5f} |
| E / 060/50 | 45.49 | {fps[1]['fps']:.2f} | {fps[1]['steps_per_second']:.5f} |

The040 result is lower; no performance tuning was included in this decision.
The retained P6 D row is45.89, rather than the integration plan's45.29 reference.
Its window starts at tick188, versus197 now; these are frame-anchored gameplay
measurements, not an isolated same-position instruction-cost comparison.
E starts at tick65 in both retained and current measurements. Both runs have zero
queue overflow. These are emulator results, not real-hardware predictions.

Evidence: `tmp/prof/p7-integration/validation.json`, `tmp/prof/p7-live/`, and their
per-run reports. The harness retains excluded setup/watchdog attempts separately.
All started emulators were closed; each run used a180-second watchdog and port2471.
Completed large snapshots are losslessly compressed. The ReadMe adds one user-facing
jump/replay-compatibility line. No additional handling candidate is pending under P7.

'''
p=Path('docs/smooth-play-plan.md');s=p.read_text();start=s.index('## P7.');end=s.index('## Not doing',start);s=s[:start]+plan+s[end:];s=s.replace('P7 stopped at its offline decision gate; A4000 handling remains unaccepted.','P7 is complete under the accepted experimental 27/29 handling decision.');p.write_text(s)
p=repo/'release/ReadMe';s=p.read_text(encoding='latin1');needle=' - Replay saving and playback for A4000 mode; original replays remain supported.\n';assert needle in s;s=s.replace(needle,needle+' - A4000 jumps are closer to A2500; older A4000 replays are incompatible.\n');p.write_text(s,encoding='latin1')
p=Path('docs/open-work.md');s=p.read_text();start=s.index('## P7 decision required');end=s.index('## Build and play',start);s=s[:start]+f'''## P7 integrated

P7 is complete under the user's accepted experimental27/29 decision. Both screened
A4000 changes are integrated for both cars, without tuning. All795 live body records
match the offline candidate in each start position. CommonY1442 and commonSpeed7719
remain failed; commonPitch11 passes. Phase failures are53/70/69. Criteria unchanged.

Replay ABI10 rejects older A4000 recordings. Fresh save/load matches1510 semantic
bytes at1500/1550/1600 plus1802 route bytes; native10/20 match1120 bytes at tick200.
The38 disabled ranges and hook audit pass. Opponent crash/restart/finish passes on
D/E without overflow (D196.60s, E86.54s with shortened idle prelude). FULL FPS is
D41.19/E45.39 against the plan's45.29/45.49; the lower040 result is recorded, not tuned.

Evidence: `tmp/prof/p7-integration/validation.json` and `tmp/prof/p7-live/`.
The authoritative P7 section records measured scope and the accepted remaining limits.
No further P7 candidate is pending. The local v2.0b archive is rebuilt, not published.

'''+s[end:];s=s.replace('6508c4d303e2edca408c7923c741d419a82c60d71f2b1d92a8b89a2c88e831d4',digest).replace('(37208 bytes)',f'({size} bytes)');p.write_text(s)
print(json.dumps(dict(slave_sha256=digest,bytes=size,lifecycles=life,fps=fps),indent=2))
