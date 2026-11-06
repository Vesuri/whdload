// Apply reviewed labels and audit hot entry functions. Args: labels.csv entries.txt
//@category AmigaXDev
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.*;
import java.nio.file.*;
public class ApplyTfxNames extends GhidraScript {
 public void run() throws Exception {
  String[] args=getScriptArgs(); int n=0;
  for(String line:Files.readAllLines(Path.of(args[0]))) {
   if(line.startsWith("offset,"))continue;
   String[] p=line.split(",",2);long o=Long.decode(p[0]);
   createLabel(toAddr(o),p[1].replace("@","at_"),true,SourceType.USER_DEFINED);n++;
  }
  for(String line:Files.readAllLines(Path.of(args[1]))) {
   Address a=toAddr(Long.decode(line));disassemble(a);
   if(getFunctionAt(a)==null)createFunction(a,null);
  }
  println("TFX labels applied: "+n);
 }
}
