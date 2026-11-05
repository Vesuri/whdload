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
| 4D Sports Driving Enhanced | JOTD | [2.0b (13.10.2026)](https://github.com/Vesuri/whdload/releases/tag/4DSportsDrivingEnhanced-2.0b-20261013) |
| Ferrari Formula One Enhanced | StingRay | not yet released |
| Formula One Grand Prix Enhanced | Codetapper | [2.0b (02.11.2026)](https://github.com/Vesuri/whdload/releases/tag/FormulaOneGrandPrixEnhanced-2.0b-20261102) |
| Grand Prix Circuit Enhanced | JOTD | [2.0b (14.10.2026)](https://github.com/Vesuri/whdload/releases/tag/GrandPrixCircuitEnhanced-2.0b-20261014) |
| Gunship Enhanced | JOTD | not yet released |
| Hard Drivin' Enhanced | JOTD | not yet released |
| Indianapolis 500 Enhanced | StingRay | [4.0b (10.10.2026)](https://github.com/Vesuri/whdload/releases/tag/Indianapolis500Enhanced-4.0b-20261010) |
| Legends of Valour Enhanced | CFou! | [2.0b (09.10.2026)](https://github.com/Vesuri/whdload/releases/tag/LegendsOfValourEnhanced-2.0b-20261009) |
| Mercenary 3 Enhanced | Harry, Graham and Wepl | [2.0b (04.11.2026)](https://github.com/Vesuri/whdload/releases/tag/Mercenary3Enhanced-2.0b-20261104) |
| Red Baron Enhanced | JOTD | [3.0b (13.10.2026)](https://github.com/Vesuri/whdload/releases/tag/RedBaronEnhanced-3.0b-20261013) |
| Road Rash Enhanced | JOTD | [3.0b (22.10.2026)](https://github.com/Vesuri/whdload/releases/tag/RoadRashEnhanced-3.0b-20261022) |
| Stellar 7 Enhanced | Psygore | not yet released |
| Test Drive Enhanced | JOTD | [2.0b (13.10.2026)](https://github.com/Vesuri/whdload/releases/tag/TestDriveEnhanced-2.0b-20261013) |
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
