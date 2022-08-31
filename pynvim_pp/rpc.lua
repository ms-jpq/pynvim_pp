return (function(gns, method, chan, uuid, ns, name)
  local global_namespace = _G[gns] or {}
  _G[gns] = global_namespace

  local namespace = _G[ns] or {}
  _G[ns] = namespace

  local m = vim[method] or vim.fn[method]

  local fn = function(...)
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

    return m[method](chan, name, unpack(argv))
  end

  namespace[name] = fn
  global_namespace[uuid] = fn
end)(...)
