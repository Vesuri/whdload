// Export the analysed program: function list, full listing and decompiled C.
// Arg0 = output directory.
//@category HardDrivin
import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;

public class HDExport extends GhidraScript {
    @Override
    public void run() throws Exception {
        String dir = getScriptArgs()[0];
        Listing listing = currentProgram.getListing();
        try (PrintWriter f = new PrintWriter(new FileWriter(dir + "/functions.txt"))) {
            for (Function fn : listing.getFunctions(true))
                f.printf("%s %s %d%n", fn.getEntryPoint(), fn.getName(), fn.getBody().getNumAddresses());
        }
        try (PrintWriter w = new PrintWriter(new BufferedWriter(new FileWriter(dir + "/listing.txt")))) {
            for (Instruction ins : listing.getInstructions(true)) {
                Symbol s = getSymbolAt(ins.getAddress());
                Function fn = getFunctionAt(ins.getAddress());
                if (fn != null) w.printf("%n; ---- %s%n", fn.getName());
                if (s != null) w.printf("%s:%n", s.getName());
                StringBuilder refs = new StringBuilder();
                for (Reference r : ins.getReferencesFrom()) {
                    if (r.getReferenceType().isFlow()) continue;
                    Symbol t = getSymbolAt(r.getToAddress());
                    if (t != null) refs.append(" ").append(t.getName());
                }
                w.printf("%s  %-40s%s%n", ins.getAddress(), ins.toString(), refs.length() > 0 ? "  ;" + refs : "");
            }
        }
        DecompInterface d = new DecompInterface();
        d.openProgram(currentProgram);
        try (PrintWriter c = new PrintWriter(new BufferedWriter(new FileWriter(dir + "/decompiled.c")))) {
            for (Function fn : listing.getFunctions(true)) {
                DecompileResults r = d.decompileFunction(fn, 60, monitor);
                c.printf("%n/* ==== %s @ %s ==== */%n", fn.getName(), fn.getEntryPoint());
                if (r != null && r.decompileCompleted()) c.print(r.getDecompiledFunction().getC());
                else c.println("/* decompile failed */");
            }
        }
    }
}
