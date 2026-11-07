#!/usr/bin/env python3
"""Summarize a tools/campaign.py run per level, and check what step 8 requires of it.

Per level: attempts (sessions), natural deaths, Continues left and game overs, kills by actor
type and native damage path, the boss's health when first sampled and its kill, player
hits with shield or cloak active, boss-helper damage calls by native caller, and how the
level ended (native exit collision into the next level, or the ending).

--require-level N checks one per-level run (CAMPAIGN_START=N, campaign.py --level N):
level N ends in a native boss kill with the boss's damage logged from deployment, then an
exit collision (the ending for level 6), with the fixture's errors at zero.

--require-complete fails unless every level 0-6 ends in a native boss kill, levels 0-5 in
an exit collision and level 6 in the ending, all with the fixture's errors at zero. All
actor damage goes through $3f04, so the boss's first logged damage call shows the
health it was deployed with: no damage, health or wave shortcut is in these builds.
"""
import argparse
import collections
import json
from pathlib import Path
import re
import struct

BOSSES = (44, 45)  # the level 1 boss switches between types 44 and 45 ($10e60)
# Return addresses into $3f04 (actor damage) by native path (docs/internals.md).
PATHS = {0x32be: 'player projectile', 0x10c5c: 'boss helper (player projectile)'}


def death_record(folder):
    """The DEATH_TEST/DEATH_RETRY records from the final memory dump."""
    folder = Path(folder)
    meta = json.loads((folder/'metadata.json').read_text())
    memory = (folder/'code.bin').read_bytes()
    code, base = meta['code_base']-meta['base'], meta['base']
    entry = struct.unpack_from('>I', memory, code+0x2af8)[0]-base
    assert memory[entry+4:entry+8] == b'S760'
    at = entry+struct.unpack_from('>H', memory, entry+104)[0]
    assert memory[at:at+4] == b'R760' and memory[at+66:at+70] == b'RN61' and memory[at+76:at+80] == b'RR60'
    stage, errors = struct.unpack_from('>2H', memory, at+4)
    count = struct.unpack_from('>H', memory, at+80)[0]
    deaths = [dict(zip(('session', 'level', 'tick'), struct.unpack_from('>HHI', memory, at+82+8*i)))
              for i in range(min(count, 32))]
    out = dict(stage=stage, errors=errors, deaths=count, recorded=deaths)
    if memory[at+338:at+342] == b'GO60':  # absent before the game-over return
        out.update(zip(('highest_level', 'return_exits', 'names_answered'), struct.unpack_from('>3H', memory, at+342)))
    return out


def report(folder):
    folder = Path(folder)
    samples = json.loads((folder/'samples.json').read_text())
    meta = json.loads((folder/'metadata.json').read_text()) if (folder/'metadata.json').exists() else {}
    session_level = {s['session']: s['level'] for s in samples}
    levels = collections.defaultdict(lambda: dict(sessions=set(), deaths=0, kills=collections.Counter(),
                                                  kill_paths=collections.Counter(), boss_first_health=None,
                                                  boss_kills=[], boss_hits=[], helper_calls=collections.Counter(),
                                                  shield_hits=0, cloak_hits=0, hits=0, exits=[], ending=[],
                                                  actor_types=set(), continues_left=[], game_overs=0,
                                                  name_entries=0, landings=[]))
    for s in samples:
        level = levels[s['level']]
        level['sessions'].add(s['session'])
        level['actor_types'].update(a[0] for a in s['actors'])
        boss = [a for a in s['actors'] if a[0] in BOSSES]
        if boss and level['boss_first_health'] is None:
            level['boss_first_health'] = dict(session=s['session'], tick=s['tick'], health=boss[0][1])
    current = None
    lines = (folder/'events.txt').read_text().splitlines()
    # $e948 also refreshes every power slot (arguments 0-6 in one tick) at session ends;
    # a landing is an argument-2 call on its own.
    refresh = {tuple(x.split()[1:3]) for x in lines if x.startswith('L ') and x.split()[-1] == '0'}
    for line in lines:
        if line.startswith('W '):  # watchdog stop
            continue
        kind, session, tick, *rest = line.split()
        session, tick = int(session), int(tick)
        lv = session_level.get(session, current)
        current = lv
        if lv is None:
            continue
        level = levels[lv]
        if kind == 'K':
            actor, health, damage, caller = int(rest[0]), int(rest[1]), int(rest[2]), int(rest[3], 16)
            level['kills'][actor] += 1
            path = PATHS.get(caller, f'{caller:#x}' if caller < 0x20000 else 'slave contact wrapper')
            level['kill_paths'][f'{path} damage {damage}'] += 1
            if actor in BOSSES:
                level['boss_kills'].append(dict(session=session, tick=tick, damage=damage, path=path))
        elif kind == 'H':
            level['boss_hits'].append(dict(session=session, tick=tick, health=int(rest[1]), damage=int(rest[2]),
                                           caller=rest[3]))
        elif kind == 'P':
            level['hits'] += 1
            level['shield_hits'] += int(rest[2]) > 0
            level['cloak_hits'] += int(rest[3]) > 0
        elif kind == 'B':
            level['helper_calls'][f'{rest[0]} from {rest[1]}'] += 1
        elif kind == 'X':
            level['exits'].append(dict(session=session, tick=tick))
        elif kind == 'D':
            level['deaths'] += 1
        elif kind == 'O':
            level['continues_left'].append(int(rest[1]))
        elif kind == 'G':
            level['game_overs'] += 1
        elif kind == 'N':
            level['name_entries'] += 1
        elif kind == 'L' and rest[4] == '2' and (str(session), str(tick)) not in refresh:
            level['landings'].append(dict(session=session, tick=tick, x=int(rest[1]), z=int(rest[2]),
                                          height=int(rest[3])))
        elif kind == 'E':
            level['ending'].append(dict(session=session, tick=tick, level=int(rest[0])))
    result = {}
    for lv in sorted(levels):
        x = levels[lv]
        result[lv] = dict(sessions=sorted(x['sessions']), deaths=x['deaths'], kills=dict(sorted(x['kills'].items())),
                          kill_paths=dict(x['kill_paths']), boss_first_sample=x['boss_first_health'],
                          boss_hits=len(x['boss_hits']),
                          boss_health_at_first_hit={s: next(h['health'] for h in x['boss_hits'] if h['session'] == s)
                                                    for s in sorted({h['session'] for h in x['boss_hits']})},
                          boss_hit_callers=dict(collections.Counter(h['caller'] for h in x['boss_hits'])),
                          boss_kills=x['boss_kills'], player_hits=x['hits'], hits_with_shield=x['shield_hits'],
                          hits_with_cloak=x['cloak_hits'], helper_calls=dict(x['helper_calls']), exits=x['exits'],
                          ending=x['ending'], continues_left=x['continues_left'], game_overs=x['game_overs'],
                          name_entries=x['name_entries'], landings=x['landings'],
                          actor_types=sorted(x['actor_types']))
    out = dict(setup=meta.get('setup'), finished=meta.get('finished'), elapsed_s=meta.get('elapsed_s'),
               samples=len(samples), levels=result)
    if (folder/'code.bin').exists():
        out['death_fixture'] = death_record(folder)
    return out


def require_level(r, lv):
    assert r['finished'] == ('ending returned' if lv == 6 else 'level left'), r['finished']
    assert r['death_fixture']['errors'] == 0, r['death_fixture']
    require_levels(r, [lv])


def require_complete(r):
    assert r['finished'] == 'ending returned', r['finished']
    assert r['death_fixture']['errors'] == 0, r['death_fixture']
    require_levels(r, range(7))


def require_levels(r, levels):
    for lv in levels:
        x = r['levels'][lv]
        assert x['boss_kills'], (lv, 'no boss kill')
        killed = x['boss_kills'][-1]['session']
        # Every actor-health change goes through $3f04, so the first logged call shows its full health.
        assert killed in x['boss_health_at_first_hit'], (lv, 'boss damage not logged from deployment')
        assert x['exits'] if lv < 6 else x['ending'], (lv, 'no native level end')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('capture', type=Path)
    p.add_argument('--require-complete', action='store_true')
    p.add_argument('--require-level', type=int)
    p.add_argument('--out', type=Path)
    a = p.parse_args()
    r = report(a.capture)
    if a.require_complete:
        require_complete(r)
    if a.require_level is not None:
        require_level(r, a.require_level)
    text = json.dumps(r, indent=1, default=str)
    if a.out:
        a.out.write_text(text+'\n')
    print(text)
