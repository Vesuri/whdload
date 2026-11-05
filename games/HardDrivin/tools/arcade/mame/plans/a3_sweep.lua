-- A3: sweep each control at standstill after the start and log the MSP inputs.
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local ev, t = { {t=24.5, log=true} }, 25
local function step(k, v) ev[#ev+1] = {t=t, [k]=v}; t = t + 0.5 end
for _, v in ipairs({0x010, 0x200, 0x400, 0x600, 0x7c0, 0x800, 0x840, 0xa00, 0xc00, 0xe00, 0xff0, 0x800}) do step("wheel", v) end
for _, v in ipairs({0x040, 0x080, 0x100, 0x180, 0x200, 0x280, 0x300, 0x400, 0x600, 0x800, 0}) do step("brake", v) end
for _, v in ipairs({16, 32, 64, 96, 128, 160, 192, 224, 255, 0}) do step("gas", v) end
for _, v in ipairs({16, 32, 64, 128, 192, 255, 0}) do step("clutch", v) end
ev[#ev+1] = {t=t, exit=true}
return S.plan(ev)
