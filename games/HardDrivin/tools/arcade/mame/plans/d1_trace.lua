-- D1: float value trace (ftrace.lua) on top of another plan. HD_BASE names the
-- plan (its own HD_* variables apply); HD_TRACE lists script times at which
-- tracing runs for HD_TRACE_LEN seconds (default 0.04, two or three frames).
-- HD_DUMP lists script times at which MSP RAM is dumped (ram_T.bin).
local tools = os.getenv("HD_TOOLS")
local ft = dofile(tools .. "/ftrace.lua")
local p = dofile(tools .. "/plans/" .. os.getenv("HD_BASE"))
local len = tonumber(os.getenv("HD_TRACE_LEN") or "0.04")
for t in string.gmatch(os.getenv("HD_TRACE") or "", "[^,]+") do
  t = tonumber(t)
  p.events[#p.events + 1] = { t=t, call=function() ft.on(true) end }
  p.events[#p.events + 1] = { t=t + len, call=function() ft.on(false) end }
end
for t in string.gmatch(os.getenv("HD_DUMP") or "", "[^,]+") do
  p.events[#p.events + 1] = { t=tonumber(t), call=function() ft.dump(t) end }
end
table.sort(p.events, function(a, b) return a.t < b.t end)
return p
