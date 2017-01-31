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
   r[9] = wrk.format(nil, "/")
   r[10] = wrk.format(nil, "/")
   r[11] = wrk.format(nil, "/")
   r[12] = wrk.format(nil, "/")
   r[13] = wrk.format(nil, "/")
   r[14] = wrk.format(nil, "/")
   r[15] = wrk.format(nil, "/")
   r[16] = wrk.format(nil, "/")
   r[17] = wrk.format(nil, "/")
   r[18] = wrk.format(nil, "/")
   r[19] = wrk.format(nil, "/")
   r[20] = wrk.format(nil, "/")
   r[21] = wrk.format(nil, "/")
   r[22] = wrk.format(nil, "/")
   r[23] = wrk.format(nil, "/")
   r[24] = wrk.format(nil, "/")
   req = table.concat(r)
end

request = function()
   return req
end
