return (function(gns, method, chan, schedule, uuid, ns, name)
  local global_namespace = _G[gns] or {}
  _G[gns] = global_namespace

  local namespace = _G[ns] or {}
  _G[ns] = namespace

  local m = vim[method] or function(...)
      vim.api.nvim_call_function(method, {...})
    end

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

    if schedule then
      vim.schedule(
        function()
          m(chan, name, unpack(argv))
        end
      )
    else
      return m(chan, name, unpack(argv))
    end
  end

  namespace[name] = fn
  global_namespace[uuid] = fn
end)(...)
