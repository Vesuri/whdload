; The shipping interrupt option changes no game instruction bytes.
; VERIFY pixel twin entry is only active with both rendering and oracle flags.
; CPUSHAPES experiment: bit 3 enters a CPU/original dispatcher (68020+ check at run time).
    IFD VERIFY
    PL_IFC5X 3
    PL_IFC2X 1
    PL_P $0f114,verify_draw_shape
    PL_ENDIF
    IFD CPUSHAPES
    PL_ELSE
    PL_IFC2X 3
    PL_P $0f114,render_cpu_dispatch
    PL_ENDIF
    ENDC
    PL_ENDIF
    ELSE
    IFD CPUSHAPES
    PL_IFC2X 3
    PL_P $0f114,render_cpu_dispatch
    PL_ENDIF
    ENDC
    ENDC
