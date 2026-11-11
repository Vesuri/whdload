# WHDLoad

Improved [WHDLoad](https://www.whdload.de) slaves for Amiga games: faster frame rates,
smoother play and fixes, each behind a `CUSTOM` option so the original behaviour stays
available. They build on slaves by other authors, who are credited in every game's docs
and release ReadMe. This repository releases the changes the original maintainers have not
taken.

Releases are on the [releases page](https://github.com/Vesuri/whdload/releases), tagged
by archive name (`WingCommanderEnhanced-2.0b-20261019`). Each archive is the original release with the slave, the
ReadMe and only the files that changed replaced. Install it as you would the original.

## Games

| Game | Original slave by | Release |
|---|---|---|
| 4D Sports Driving Enhanced | JOTD | [2.0b (10.11.2026)](https://github.com/Vesuri/whdload/releases/tag/4DSportsDrivingEnhanced-2.0b-20261110) |
| Battlehawks 1942 Enhanced | Galahad/Fairlight | [2.0b (09.11.2026)](https://github.com/Vesuri/whdload/releases/tag/Battlehawks1942Enhanced-2.0b-20261109) |
| Buggy Boy Enhanced | Codetapper | [2.0b (11.11.2026)](https://github.com/Vesuri/whdload/releases/tag/BuggyBoyEnhanced-2.0b-20261111) |
| Encounter Enhanced | JOTD | not yet released |
| Ferrari Formula One Enhanced | StingRay | [2.0b (11.11.2026)](https://github.com/Vesuri/whdload/releases/tag/FerrariFormulaOneEnhanced-2.0b-20261111) |
| Formula One Grand Prix Enhanced | Codetapper | [2.0b (11.11.2026)](https://github.com/Vesuri/whdload/releases/tag/FormulaOneGrandPrixEnhanced-2.0b-20261111) |
| Grand Prix Circuit Enhanced | JOTD | [2.0b (14.10.2026)](https://github.com/Vesuri/whdload/releases/tag/GrandPrixCircuitEnhanced-2.0b-20261014) |
| Gunship Enhanced | JOTD | not yet released |
| Hard Drivin' Enhanced | JOTD | [4.0b (06.11.2026)](https://github.com/Vesuri/whdload/releases/tag/HardDrivinEnhanced-4.0b-20261106) |
| Indianapolis 500 Enhanced | StingRay | [4.0b (11.11.2026)](https://github.com/Vesuri/whdload/releases/tag/Indianapolis500Enhanced-4.0b-20261111) |
| Legends of Valour Enhanced | CFou! | [2.0b (09.11.2026)](https://github.com/Vesuri/whdload/releases/tag/LegendsOfValourEnhanced-2.0b-20261109) |
| Mercenary 3 Enhanced | Harry, Graham and Wepl | [2.0b (09.11.2026)](https://github.com/Vesuri/whdload/releases/tag/Mercenary3Enhanced-2.0b-20261109) |
| Powerdrome Enhanced | Galahad/Fairlight | [2.0b (10.11.2026)](https://github.com/Vesuri/whdload/releases/tag/PowerdromeEnhanced-2.0b-20261110) |
| Prince of Persia Enhanced | JOTD | released upstream as JOTD's 5.2 (24.10.2026) |
| Red Baron Enhanced | JOTD | [3.0b (13.10.2026)](https://github.com/Vesuri/whdload/releases/tag/RedBaronEnhanced-3.0b-20261013) |
| Road Rash Enhanced | JOTD | [3.0b (11.11.2026)](https://github.com/Vesuri/whdload/releases/tag/RoadRashEnhanced-3.0b-20261111) |
| Robinson's Requiem Enhanced | CFou! | not yet released |
| Star Wars Enhanced | StingRay | not yet released |
| Stellar 7 Enhanced | Psygore | [2.0b (07.11.2026)](https://github.com/Vesuri/whdload/releases/tag/Stellar7Enhanced-2.0b-20261107) |
| Test Drive Enhanced | JOTD | [2.0b (13.10.2026)](https://github.com/Vesuri/whdload/releases/tag/TestDriveEnhanced-2.0b-20261013) |
| Test Drive II Enhanced | JOTD | released upstream as JOTD's 2.1 (11.10.2026) |
| TFX Enhanced | JOTD | not yet released; merged upstream, not released there |
| Their Finest Hour Enhanced | Psygore | [2.0b (13.10.2026)](https://github.com/Vesuri/whdload/releases/tag/TheirFinestHourEnhanced-2.0b-20261013) |
| Wing Commander Enhanced | Psygore | [2.0b (19.10.2026)](https://github.com/Vesuri/whdload/releases/tag/WingCommanderEnhanced-2.0b-20261019) |

## Building

The slaves are built on macOS with the environment from
[AmigaXDev](https://github.com/Vesuri/amigaxdev)'s `make setup` (vasm, WHDLoad's developer
package, FS-UAE). No game data, Kickstart or WHDLoad files are in this repository: supply
the original archives yourself.

```sh
make list                                   # the games
cd games/<Game>
make unpack ARCHIVES=<directory with the original archives>
make slave                                  # tmp/build/release/
make run SETUP=a1200                        # boot it in FS-UAE
make dist                                   # repack the original archives into dist/
```

`docs/index.md` describes the layout, running, building and releasing.
