from pathlib import Path
p=Path('release'); t=Path('tmp/g-template')
f=p/'source/RoadRashHD.s'; s=f.read_text(); start=s.index('\tIFD BARFLY\n\tDOSCMD'); end=s.index('\n_name',start)
s=s[:start]+'DECL_VERSION:MACRO\n\tdc.b\t"3.0b (22.10.2026)"\n\tENDM\n'+s[end:];f.write_text(s)
s=(t/'Install').read_text(encoding='latin1').replace('(set #sub-dir "")','(set #sub-dir "data")')
for a,b in [('20 "colicon"','20 "coloricon"'),('21 "colicon2"','21 "glowicon"'),('24 "colexot"','24 "exoticon"'),('21 "OS3.5 Icon 2"','21 "Glow Icon"'),('24 "OS3.5 Exotica"','24 "Exoticon"')]:s=s.replace(a,b)
s=s.replace('(set #icon_set_slave_preload "")','(set #icon_set_slave_preload "true")')
a=s.index('      ;if the disk can be requested');b=s.index('\n    (\t\t\t\t;----- 4 = CD',a)
s=s[:a]+'''      ; Both disk-label variants supported by the version 2.0 installer.
      (set #disk-label
        (askchoice
          (prompt "How is disk #1 labelled?")
          (default 0)
          (choices "rr1" "Road Rash")
          (help @askchoice-help)
        )
      )
      (select #disk-label
        (set #AD_disk "rr1")
        (set #AD_disk "Road Rash")
      )
      (set #AD_diskname "Disk 1")
      (P_AskDisk)
      (copyfiles
        (help @copyfiles-help)
        (source ("%s:" #AD_disk))
        (dest #dest)
        (pattern "#?")
      )
      (set #AD_disk "roadrash")
      (set #AD_diskname "Disk 2")
      (P_AskDisk)
      (copyfiles
        (help @copyfiles-help)
        (source ("%s:data" #AD_disk))
        (dest #dest)
        (pattern "#?")
      )
    )
''' +s[b:]
# A declined replacement must not silently merge into an installation with saves.
s=s.replace('(if (exists #dest) (','(if (or (exists #dest) (exists (cat #dest ".info"))) (')
s=s.replace('"Should it be deleted?"','"Replace this installation and its drawer icon?\\nSaved games in it will be deleted."')
s=s.replace('(choices "Delete" "Skip")','(choices "Replace" "Cancel")').replace('(default 1)\n      (choices "Replace"','(default 0)\n      (choices "Replace"')
needle='    (run ("Delete \\"' # direct insertion after exact line
line='    (run ("Delete \\"'
old='    (run ("Delete \\"'
actual='    (run ("Delete \\"'
# The template uses escaped double quotes in its shell command.
pos=s.index('    (run ("Delete ', s.index('(if (or (exists #dest)'))
end=s.index('\n',pos)
s=s[:end]+'\n    (abort "Installation cancelled; existing installation retained.")'+s[end:]
(p/'Install').write_bytes(s.encode('latin1'))
old=(p/'Readme').read_bytes().decode('latin1').replace('\r\n','\n')
history=old[old.index(' Version 2.0'):old.index('CD32 controls - menu:')].rstrip()
controls=old[old.index('CD32 controls - menu:'):].rstrip()
template=(t/'ReadMe').read_text(encoding='latin1')
readme=template[:template.index(' This install applies')]+''' This install applies to "Road Rash" (c) 1992 Electronic Arts - 2 disks.

 Requirements:
 -------------
 WHDLoad 17.2 or newer must be installed in the path.
 The installed program requires 1 MB ChipMem and memory for WHDLoad and the
 slave. Enhanced framerate uses an optional 564 KB OtherMem allocation;
 Fast RAM and a 68020 or faster are recommended. PRELOAD needs additional
 memory for the game files. No Kickstart image is required by this slave.
 Quit with Help (changeable with the WHDLoad QuitKey tooltype).

 Features:
 ---------
 Runs from hard disk, with disk protection removed. Supports joystick,
 keyboard arrows and CD32 joypad, including name and password entry.
 The original manual and a choice of five icons are included.

 Options:
 --------
 CUSTOM1 selects one of the preset passwords in the WHDLoad startup options.
 CUSTOM accepts a user-defined password; see the format and examples below.
 CUSTOM2=1 enables "Enhanced framerate". It is off by default; omit CUSTOM2
 or use CUSTOM2=0 for original timing and rendering.

 With Enhanced framerate, 68020+ machines with suitable Fast RAM render as
 fast as they can while retaining vsync. The simulation advances in fixed
 20 ms PAL steps and catches up when rendering takes longer. There is no
 added frame limiter or delayed interpolation. Rider heading is predicted
 for display to reduce visible steering lag. Opponent paths and collision
 outcomes can differ because lane occupancy now uses actor widths.

 Caches are enabled automatically on the enhanced accelerated path unless
 NoCache is specified. A 68000 with suitable Fast RAM can benefit from faster
 rendering while retaining the original simulation. Chip-only machines and
 unavailable/unsuitable optional memory use the original path. Input,
 loading and ECS/AGA border fixes also apply when CUSTOM2 is off.

 Performance (emulated PAL, first race, 500 fields of full throttle):
 -----------------------------------------------------------------
 MACHINE                  ORIGINAL 2.0    ENHANCED 3.0b (fps)
 [FINAL RELEASE MEASUREMENTS]
 These are scene-specific emulator measurements, not minimum frame rates or
 real-hardware guarantees. Physical 68040/68060 cache testing remains pending.

'''+controls+'''

 History:
 --------
 Version 3.0b (22.10.2026):
 - optional Enhanced framerate for smoother, vsynced play on Fast RAM Amigas
 - consistent simulation speed on the accelerated path, with reduced visible
   steering lag and corrected opponent lane occupancy
 - fixed joystick steering recentring and keyboard/CD32 pause handling
 - fixed a loading crash on uncached 68030 machines
 - blanked the border during play on ECS/AGA machines

'''+history+'\n\n'+template[template.index(' Contact:'):]
(p/'Readme').write_bytes(readme.replace('\n','\r\n').encode('latin1'))
