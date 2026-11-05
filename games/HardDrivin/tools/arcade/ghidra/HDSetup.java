// Pre-analysis setup for the Hard Drivin' rev 7 68010 image: memory blocks for
// the driver board I/O and RAM (from MAME's driver_68k_map and init_adsp/
// init_driver_sound), register labels, and the exception vectors.
//@category HardDrivin
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.SourceType;

public class HDSetup extends GhidraScript {
    void block(String name, long start, long size, boolean io) throws Exception {
        MemoryBlock b = currentProgram.getMemory().createUninitializedBlock(name, toAddr(start), size, false);
        b.setRead(true); b.setWrite(true); b.setVolatile(io);
    }
    void label(long a, String n) throws Exception { createLabel(toAddr(a), n, true, SourceType.USER_DEFINED); }
    @Override
    public void run() throws Exception {
        block("IO_600000", 0x600000, 0x10000, true);
        block("ADSP", 0x800000, 0x40000, true);
        block("SOUND", 0x840000, 0x10000, true);
        block("IO_A00000", 0xa00000, 0x200000, true);
        block("HOSTIO", 0xc00000, 0x8000, true);
        block("DUART", 0xff0000, 0x20, true);
        block("ZRAM", 0xff4000, 0x1000, false);
        block("RAM", 0xff8000, 0x8000, false);
        label(0x600000, "IN0_port0"); label(0x600002, "SW1_port0");
        label(0x604000, "NWR"); label(0x608000, "WATCHDOG"); label(0x60c000, "IRQ_ACK");
        label(0x800000, "ADSP_PGM"); label(0x808000, "ADSP_DATA"); label(0x810000, "ADSP_BUFFER");
        label(0x818000, "ADSP_CONTROL"); label(0x818060, "ADSP_IRQ_CLEAR"); label(0x838000, "ADSP_IRQ_STATE");
        label(0x840000, "SND_DATA"); label(0x844000, "SND_STATUS"); label(0x84c000, "SND_RESET");
        label(0xa00000, "WR0"); label(0xa80000, "IN_A80000_WR1"); label(0xb00000, "ADC8_WR2");
        label(0xb80000, "ADC12"); label(0xc00000, "GSP_HOSTIO"); label(0xc04000, "MSP_HOSTIO");
        label(0xff0000, "DUART"); label(0xff4000, "ZRAM_EEPROM");
        // The boot ROM hands over to the game through a second vector table at
        // $16000; $16100 holds jumps to the alternative game entry points.
        for (long a : new long[]{0x16100, 0x16106, 0x1610c, 0x3c5e0, 0x3c668, 0x3c6ae, 0x3c6f4}) {
            disassemble(toAddr(a));
            if (getFunctionAt(toAddr(a)) == null) createFunction(toAddr(a), "entry_" + Long.toHexString(a));
        }
        vectors(0x16000, "game_");
        vectors(0, "");
    }
    void vectors(long base, String pre) throws Exception {
        String[] vn = {"SSP","RESET","BUS_ERROR","ADDRESS_ERROR","ILLEGAL","ZERO_DIVIDE","CHK","TRAPV",
            "PRIVILEGE","TRACE","LINE_A","LINE_F"};
        for (int i = 0; i < 64; i++) {
            Address va = toAddr(base + i * 4);
            createDWord(va);
            long t = getInt(va) & 0xffffffffL;
            String n = i < vn.length ? vn[i] : (i >= 24 && i < 32 ? "AUTOVEC" + (i - 24) : (i >= 32 && i < 48 ? "TRAP" + (i - 32) : "VEC" + i));
            label(base + i * 4, pre + "vec_" + n);
            if (i == 0 || t == 0 || t >= 0x100000 || (t & 1) != 0) continue;
            Address ta = toAddr(t);
            if (getFunctionAt(ta) == null) {
                disassemble(ta);
                createFunction(ta, pre + "h_" + n + "_" + Long.toHexString(t));
            }
        }
    }
}
