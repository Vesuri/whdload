; Production coarse entries: 68000 200 ms / chip-only 68020 100 ms.
 include "FerrariFormulaOne_CoarseInstall.s"
 include "ProductionFault.s"
selection_path: dc.l 1
selection_interval: dc.l 100
 include "FerrariFormulaOne_Coarse.s"

public_table: dc.l 0
public_bound: dc.l 0
 include "FerrariFormulaOne_PublicPatches.s"
 include "FerrariFormulaOne_PublicMemory.s"
 include "FerrariFormulaOne_Bindings.s"
public_bindings:
 incbin "bindings.bin"

 IFD FF1_COARSE_200_COMPLETE
 include "FerrariFormulaOne_Coarse200RootTable.s"
 include "FerrariFormulaOne_Coarse200DivideTable.s"

 ENDC
