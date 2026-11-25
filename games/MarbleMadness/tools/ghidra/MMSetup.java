// Mark code hunk starts as functions (hunk map from mm.bin.json), data hunks as data.
//@category MM
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import java.nio.file.*;
import java.util.regex.*;
public class MMSetup extends GhidraScript {
    public void run() throws Exception {
        String js = new String(Files.readAllBytes(Paths.get(getScriptArgs()[0])));
        Matcher m = Pattern.compile("\"i\": (\\d+),\\s*\"type\": \"(\\w+)\",\\s*\"base\": (\\d+),\\s*\"size\": (\\d+)").matcher(js);
        int n = 0;
        while (m.find()) {
            String t = m.group(2); long base = Long.parseLong(m.group(3)); long size = Long.parseLong(m.group(4));
            if (size == 0) continue;
            Address a = toAddr(base);
            createLabel(a, "hunk" + m.group(1) + "_" + t, true);
            if (t.equals("CODE")) { disassemble(a); createFunction(a, null); n++; }
        }
        println("code hunks: " + n);
    }
}
