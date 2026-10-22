# Current work

Repository and input preparation are complete. Analysis is deliberately deferred.
Both supplied archives are retained, pinned and extracted. No source reading,
disassembly, executable inspection, emulator boot, trace, profile or patch work
has been performed.

The initial assumption that slave source was unavailable is corrected by the
installer archive listing: it contains both slave and imager assembly files.
The official page credits Harry, Graham and Wepl, with version 1.2 by Wepl.

## When investigation is requested

1. Inspect the supplied source and establish whether it rebuilds the shipped slave.
2. Identify the slave requirements, game code and supported versions.
3. Add a project-specific launcher using the shared environment and process helper.
4. Establish a reproducible boot and gameplay route before measuring or changing code.

Do not execute these steps under the setup-only request.
