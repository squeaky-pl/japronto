require "http/server"

server = HTTP::Server.new("0.0.0.0", 8080) do |context|
  case context.request.path
  when "/"
    context.response.status_code = 200
    context.response.print "Hello world!"
  else
    context.response.status_code = 404
    context.response.print "Not Found"
  end
end

server.listen
