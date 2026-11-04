 This install applies to "Mercenary 3 - The Dion Crisis" © 1991 Novagen.

 Requirements:
 -------------
 This install requires WHDLoad version 17 and RawDIC to be in the path.
 Both programs can be found in the WHDLoad package.
 To install from a different drive than DF0: select installation mode Expert.

 The installed program requires 0.5 MB ChipMem and 0.5 MB OtherMem, plus
 memory for preloading the disk image and 288 KB for the optional Enhanced
 framerate workspace. The tested A500 has 1.5 MB OtherMem.
 It can be quit by pressing BACKSPACE (key can be changed with Tooltype
 "QuitKey=").

 Features:
 ---------
 Saved games are stored on HD, in the game drawer. Keep it writable and back
 up saved games before reinstalling.

 Enhanced framerate draws extra frames between the game's own updates, so
 walking, driving and flying move more smoothly, while the game world keeps
 its original speed. It is on by default: the installed icon has the
 Tooltype "Custom5=1". To keep the original behaviour, set "Custom5=0",
 remove the Tooltype or uncheck "Enhanced framerate" in the WHDLoad splash
 window; the fixes listed below for version 2.0b apply in both settings.

 Enhanced framerate benefits most from a 68020 or later with Fast RAM and
 the Tooltype "Cache". Rendering can reach 50 frames per second PAL on
 suitable machines and scenes; this is not guaranteed. Smooth frames show
 completed movement, which adds about 80 ms of visual delay, instead of
 predicting past stops and collisions. Enclosed rooms are drawn at the
 game's own frame rate. If the workspace can't be allocated, the game still
 runs, without the extra frames. AGA-specific optimisations are used only
 on AGA machines. NOCACHE can be used for cache troubleshooting.

 Version 2.0b was tested in emulation on 68000, 68020, 68030, 68040 and 68060
 configurations. No real hardware was available; real-hardware cache
 behaviour and 68040/68060 performance remain unverified.

 History:
 --------
 version 2.0b (04.11.2026) done by Vesuri:
 - new option Enhanced framerate, enabled in the installed icon: faster
   rendering, and smoother walking, vehicles, flight, doors and shots,
   without speeding up the game world; with it, the Tooltype Cache also
   enables the data cache on 68030 and later
 - fixed the display routine, which waited for a vertical blank every frame
   and left part of each frame's colour update undone
 - fixed intermittently missing ground with caches on 68040/68060
 - WHDLoad 17 is required
