 This install applies to "Mercenary 3 - The Dion Crisis" (c) 1991 Novagen.

 Requirements:
 -------------
 WHDLoad version 17 or later and RawDIC must be in the path.
 Both programs are included in the WHDLoad package.
 To install from a drive other than DF0: select Expert installation mode.

 The game requires a 68000 or later and 0.5 MB ChipMem, plus memory for
 WHDLoad and preloading the disk image. The original install specifies
 0.5 MB OtherMem; allow additional memory for PRELOAD and the optional
 288 KB enhancement workspace. The tested A500 has 1.5 MB OtherMem.
 No Kickstart image is required by this slave.

 Enhanced framerate benefits most from a 68020 or later with Fast RAM.
 If the optional workspace cannot be allocated, the game still runs,
 without intermediate presentation frames. AGA-specific optimisations
 are enabled only on AGA machines.

 Quit with BACKSPACE (change it with the "QuitKey=" tooltype).

 Features:
 ---------
 - Hard disk loading and saved games.
 - Enhanced framerate: faster rendering and smoother movement while
   walking, driving and flying, with game logic at its native speed.
 - Fast RAM, AGA and cache support selected for the available hardware.
 - Return to the operating system with the quit key.

 The installer enables the "Enhanced framerate" checkbox by default.
 Set it to Off for the original game behaviour; fixes for the old
 slave's display bugs stay active. The equivalent tooltype
 is CUSTOM5=1 for On or CUSTOM5=0 for Off; omission also means Off.
 Old CUSTOM1 settings are ignored.
 Smooth frames use completed movement, adding about 80 ms of visual delay
 on fast machines instead of predicting past stops and collisions.
 Rendering can reach 50 fps PAL on suitable machines and scenes; this is
 not a guaranteed frame rate. The installer enables CACHE and PRELOAD.
 NOCACHE can be used for cache troubleshooting.

 Saved situations are stored in the game drawer. Keep it writable and
 back up saved games before reinstalling. The install includes the manual,
 transport guide, short solution and illustrated HTML solution.

 Tested in emulation on 68000, 68020, 68030, 68040 and 68060 configurations.
 No real hardware was available for version 2.0 testing; real-hardware
 cache behaviour and 68040/68060 performance remain unverified.

 History:
 --------
 version 2.0 (23.10.2026) by Vesuri:
 - Faster rendering and smoother walking, vehicles and flight, without
   speeding up the game world.
 - Added "Enhanced framerate", enabled by default; Off restores original
   behaviour.
 - Smoothed room-wall movement to match the interpolated camera.
 - Fixed intermittent missing ground with caches enabled on 68040/68060.
 - Updated installer, with CACHE and PRELOAD enabled in the game icon.

