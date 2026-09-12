var express = require('express');
var request = require('request');
var app = express();
var http = require('http').Server(app);
var io = require('socket.io')(http);
var path = require('path');

// Target IPv6 of the websense edge device
// Can be passed via command line argument: node index.js fd00::xxxx...
// or via environment variable: NODE_IP=fd00::xxxx node index.js
var targetIp = process.argv[2] || process.env.NODE_IP || 'fd00::f6ce:3648:1501:373e';
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
