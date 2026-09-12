var express = require('express');
var request = require('request');
var app = express();
var http = require('http').Server(app);
var io = require('socket.io')(http);
var path = require('path');

// Target IPv6 of the websense edge device
// Priority:
// 1. Command-line argument: node index.js fd00::xxxx
// 2. NODE_IP environment variable
// 3. CONTIKI_NODES environment variable (injected by Pi sandbox)
// 4. Fallback default
var contikiNode = process.env.CONTIKI_NODES ? process.env.CONTIKI_NODES.split(',')[0].trim() : null;
var targetIp = process.argv[2] || process.env.NODE_IP || contikiNode || 'fd00::f6ce:3648:1501:373e';
var targetUrl = 'http://[' + targetIp + ']/';

console.log('Target Websense Node URL:', targetUrl);

app.use(express.static(path.join(__dirname, 'public')));

app.get('/', function(req, res){
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

io.on('connection', function(socket) {
    console.log('Client connected to visualization web UI');

    var dataPusher = setInterval(function () {
        request.get({ url: targetUrl, timeout: 2500 }, function(err, res, body){
            if(err){
                console.log('Polling error:', err.message || err);
                return;
            }
            try {
                var obj = JSON.parse(body);
                console.log('Received sensor data:', obj);
                // Emit to connected web clients
                socket.emit('data', obj.temp);
                socket.broadcast.emit('data', obj.temp);
            } catch(e) {
                console.log('Invalid JSON received:', body);
            }
        });
    }, 3000);

    socket.on('disconnect', function() {
        console.log('Client disconnected');
        clearInterval(dataPusher);
    });
});

http.listen(3000, function(){
    console.log('Visualization server running on http://localhost:3000');
    console.log('Usage: node index.js [WEBSENSE_NODE_IPV6]');
});
