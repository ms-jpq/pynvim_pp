return (function(prefix, ext, ...)
  local method = prefix .. "_call"
  local argv = {...}
  local fn = function()
    --$BODY
  end
  return vim.api[method](ext, fn)
end)(...)
