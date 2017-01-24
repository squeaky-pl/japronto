-- example script demonstrating HTTP pipelining

init = function(args)
   local r = {}
   r[1] = wrk.format(nil, "/")
   r[2] = wrk.format(nil, "/")
   r[3] = wrk.format(nil, "/")
   r[4] = wrk.format(nil, "/")
   r[5] = wrk.format(nil, "/")
   r[6] = wrk.format(nil, "/")   
   r[7] = wrk.format(nil, "/")
   r[8] = wrk.format(nil, "/")

   req = table.concat(r)
end

request = function()
   return req
end
