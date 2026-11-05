-- D1: log MSP writes to HD_WATCH (FROM-TO, hex bit addresses) with the PC
-- and emulated time, on top of the plan HD_BASE (watch.txt).
local tools = os.getenv("HD_TOOLS")
local p = dofile(tools .. "/plans/" .. os.getenv("HD_BASE"))
local m = manager.machine
local cpu = m.devices[":mainpcb:msp"]
local msp = cpu.spaces["program"]
local out = io.open(os.getenv("HD_RUN") .. "/watch.txt", "w")
local a, b = string.match(os.getenv("HD_WATCH"), "(%x+)-(%x+)")
local n = 0
d1_watch = msp:install_write_tap(tonumber(a, 16), tonumber(b, 16), "d1w", function(offset, data, mask)
  n = n + 1
  if n > 20000 then return end
  out:write(string.format("%.6f %06x %04x pc=%06x\n", m.time:as_double(), offset, data, cpu.state["PC"].value & 0xffffff))
  out:flush()
end)
return p
