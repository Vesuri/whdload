; The shipping interrupt option changes no game instruction bytes.
; VERIFY pixel twin entry is only active with both rendering and oracle flags.
    IFD VERIFY
    PL_IFC2X 1
    PL_IFC5X 3
    PL_P $0f114,verify_draw_shape
    PL_ENDIF
    PL_ENDIF
    ENDC
