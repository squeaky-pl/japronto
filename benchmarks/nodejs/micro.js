const http = require('http');


var srv = http.createServer( (req, res) => {
  res.sendDate = false;
  data = 'Hello world!'
  res.writeHead(200, {
    'Content-Type': 'text/plain; encoding=utf-8',
    'Content-Length': data.length});
  res.end(data);
});


srv.listen(8080, '0.0.0.0');
