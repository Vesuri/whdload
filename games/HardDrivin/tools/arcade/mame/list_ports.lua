-- Print all input ports and fields, then exit.
for tag, port in pairs(manager.machine.ioport.ports) do
  for name, f in pairs(port.fields) do
    print(string.format("%s | %s | mask=%x default=%x analog=%s min=%s max=%s", tag, name, f.mask, f.defvalue, tostring(f.is_analog), tostring(f.minvalue), tostring(f.maxvalue)))
  end
end
for tag, d in pairs(manager.machine.devices) do
  if d.spaces and next(d.spaces) then
    local s = {} for n in pairs(d.spaces) do s[#s+1]=n end
    print("device " .. tag .. " spaces " .. table.concat(s, ","))
  end
end
manager.machine:exit()
