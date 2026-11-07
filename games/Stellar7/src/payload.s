; One fixed-rate simulation, assembled alone (-Fbin, game.sh) with a development variant's
; defines. The release Stellar7.slave carries two and installs the one for the CPU
; (Stellar7.s). Offset 0 is timing_install, called as from the development slaves; the last
; long is this copy's _resload, which the loader fills first.
        INCLUDE whdload.i
        INCLUDE whdmacros.i
        INCLUDE lvo/exec.i
        INCLUDE exec/execbase.i
        INCLUDE sim60.s
payload_end:
        CNOP 0,4
_resload: dc.l 0
