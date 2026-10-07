 version 1.6b (07.10.2026) done by Vesuri:
 - added the "Enhanced framerate" option (CUSTOM2), for the version of the game
   whose "duel" file is 108868 bytes long (the other version is unchanged):
   - the game logic runs at a fixed rate, independently of drawing: every 6
     frames (the original rate) on a 68000, every 2 frames on a 68020 or better.
     Faster machines draw more frames without changing the game speed
   - the blitter gets bus priority and unused blitter interrupts are removed
   - the road and cars are drawn at fractional positions for smoother motion
   - sideways motion (steering, lane position and mountains) and hill crests
     are smooth as well
   - measured in the first race: A500 7.1 fps (6.1 without the option),
     A1200 16.7 fps, 68030/25 MHz 25 fps until the car is at speed
   - after a crash or engine damage, the player's car recovers in about 5
     seconds with a 20 second time penalty, while the opponent and the clock
     keep running
   The icon enables it with the tooltype CUSTOM2=1. Remove it, or set
   CUSTOM2=0, to run the original game
 - fixed the cars jumping 16 pixels to the left for one frame in the
   introduction (an original bug: DDFSTOP was changed too late on the line
   above the car)
 - the slave is built from the official WHDLoad 20.0 KickEmu/API sources, but
   still runs with WHDLoad 17.2 or later. The installer source package includes
   the matching public-domain headers and KickEmu sources

