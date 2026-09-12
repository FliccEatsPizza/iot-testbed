var express = require('express');
var request = require('request');
var app = express();
var http = require('http').Server(app);
var io = require('socket.io')(http);
var path = require('path');

// ============================================================================
// Configuration
// ============================================================================

// 1. Target IPv6 of the websense edge device
// Priority: Command-line arg 1 -> NODE_IP env -> CONTIKI_NODES env -> Fallback
var contikiNode = process.env.CONTIKI_NODES ? process.env.CONTIKI_NODES.split(',')[0].trim() : null;
var targetIp = process.argv[2] || process.env.NODE_IP || contikiNode || 'fd00::f6ce:3648:1501:373e';
var targetUrl = 'http://[' + targetIp + ']/';

// 2. ThingSpeak Cloud Configuration
// Priority: Command-line arg 2 -> THINGSPEAK_API_KEY env
var thingspeakApiKey = process.argv[3] || process.env.THINGSPEAK_API_KEY || null;

var lastThingspeakUpload = 0;
var THINGSPEAK_INTERVAL_MS = 15000; // ThingSpeak free tier rate limit: 15s between updates

console.log('====================================================');
console.log(' 🌐 IoT Sandbox Gateway & ThingSpeak Forwarder');
console.log('====================================================');
console.log('📍 Target Edge Mote URL  :', targetUrl);
if (thingspeakApiKey) {
    console.log('☁️  ThingSpeak Cloud Sync  : ENABLED (Write Key: ' + thingspeakApiKey.substring(0, 4) + '****)');
} else {
    console.log('☁️  ThingSpeak Cloud Sync  : DISABLED (Set THINGSPEAK_API_KEY or pass as 2nd argument)');
}
console.log('====================================================\n');

// ============================================================================
// Web Server & Static Files
// ============================================================================
app.use(express.static(path.join(__dirname, 'public')));

app.get('/', function(req, res){
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Status endpoint for health checks
app.get('/status', function(req, res){
    res.json({
        targetIp: targetIp,
        thingspeakEnabled: Boolean(thingspeakApiKey),
        timestamp: new Date().toISOString()
    });
});

io.on('connection', function(socket) {
    console.log('👤 Client connected to local visualization web UI');
    socket.on('disconnect', function() {
        console.log('👤 Client disconnected from local web UI');
    });
});

// ============================================================================
// ThingSpeak Cloud Forwarding Function
// ============================================================================
function uploadToThingSpeak(apiKey, temp, hum) {
    var tsUrl = 'https://api.thingspeak.com/update';
    request.post({
        url: tsUrl,
        form: {
            api_key: apiKey,
            field1: temp, // Field 1: Temperature
            field2: hum   // Field 2: Humidity
        },
        timeout: 5000
    }, function(err, res, body) {
        if (err) {
            console.error('☁️ [ThingSpeak] Upload error:', err.message || err);
        } else if (body === '0' || !res || res.statusCode !== 200) {
            console.warn('⚠️  [ThingSpeak] Update rejected or rate-limited (Response: ' + body + ')');
        } else {
            console.log('☁️ [ThingSpeak] Upload successful! Entry ID: #' + body.trim() + ' (Temp: ' + temp + '°C, Hum: ' + hum + '%)');
        }
    });
}

// ============================================================================
// Background Polling Loop (Runs continuously in the sandbox)
// ============================================================================
setInterval(function () {
    request.get({ url: targetUrl, timeout: 2500 }, function(err, res, body){
        if (err) {
            console.log('⚠️  Polling error from [' + targetIp + ']:', err.message || err);
            return;
        }
        try {
            var obj = JSON.parse(body);
            console.log('📥 Sensor Reading: Temp=' + obj.temp + '°C, Hum=' + obj.hum + '%');

            // 1. Send to all connected web UI clients in real-time
            io.emit('data', obj.temp);

            // 2. Upload to ThingSpeak cloud (respecting 15s rate limit)
            if (thingspeakApiKey) {
                var now = Date.now();
                if (now - lastThingspeakUpload >= THINGSPEAK_INTERVAL_MS) {
                    lastThingspeakUpload = now;
                    uploadToThingSpeak(thingspeakApiKey, obj.temp, obj.hum);
                }
            }
        } catch(e) {
            console.log('⚠️  Invalid JSON received:', body);
        }
    });
}, 3000);

// ============================================================================
// Start Server
// ============================================================================
http.listen(3000, function(){
    console.log('🚀 Local visualization server running on http://localhost:3000');
    console.log('Usage: node index.js [WEBSENSE_NODE_IPV6] [THINGSPEAK_API_KEY]\n');
});
