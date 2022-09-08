return (function(gns, lua_method, ...)
  local global_namespace = _G[gns] or {}

  local argv = {...}
  for i, arg in ipairs(argv) do
    if type(arg) == "table" then
      local maybe_fn = arg[gns]
      if type(maybe_fn) == "string" then
        local trampoline = function(...)
          return global_namespace[maybe_fn](...)
        end
        argv[i] = trampoline
      end
    end
  end

  local acc = _G
  for name in vim.gsplit(lua_method, ".", true) do
    acc = acc[name]
  end
  return acc(unpack(argv))
end)(...)
