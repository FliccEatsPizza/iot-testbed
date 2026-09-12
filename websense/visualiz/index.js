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
var contikiNode = process.env.CONTIKI_NODES ? process.env.CONTIKI_NODES.split(',')[0].trim() : null;
var targetIp = process.argv[2] || process.env.NODE_IP || contikiNode || 'fd00::f6ce:3648:1501:373e';
var targetUrl = 'http://[' + targetIp + ']/';

// 2. ThingSpeak Telemetry Configuration (Channel Write API)
var thingspeakApiKey = process.argv[3] || process.env.THINGSPEAK_API_KEY || null;

// 3. ThingSpeak TalkBack Configuration (Cloud Actuation API)
var talkbackId = process.argv[4] || process.env.TALKBACK_ID || null;
var talkbackApiKey = process.argv[5] || process.env.TALKBACK_API_KEY || null;

var lastThingspeakUpload = 0;
var THINGSPEAK_INTERVAL_MS = 15000; // Rate limit: 15s between channel updates

console.log('====================================================');
console.log(' 🌐 IoT Sandbox Gateway — Telemetry & Cloud Actuation');
console.log('====================================================');
console.log('📍 Target Edge Mote URL   :', targetUrl);
if (thingspeakApiKey) {
    console.log('☁️  ThingSpeak Channel Sync : ENABLED (Key: ' + thingspeakApiKey.substring(0, 4) + '****)');
} else {
    console.log('☁️  ThingSpeak Channel Sync : DISABLED');
}

if (talkbackId && talkbackApiKey) {
    console.log('⚡ ThingSpeak TalkBack Sync : ENABLED (TalkBack ID: ' + talkbackId + ')');
} else {
    console.log('⚡ ThingSpeak TalkBack Sync : DISABLED (Set TALKBACK_ID and TALKBACK_API_KEY)');
}
console.log('====================================================\n');

// ============================================================================
// Web Server & Static Files
// ============================================================================
app.use(express.static(path.join(__dirname, 'public')));

app.get('/', function(req, res){
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// ============================================================================
// Actuation Helper Function (Forwards to Physical Edge Device over IPv6 tun0)
// ============================================================================
function actuateEdgeDevice(action, source, callback) {
    var actuateUrl = 'http://[' + targetIp + ']/led/' + action;
    console.log('👉 [' + source + '] Sending actuation to mote:', actuateUrl);

    request.get({ url: actuateUrl, timeout: 3000 }, function(err, res, body) {
        if (err) {
            console.error('❌ Actuation failed on mote [' + targetIp + ']:', err.message || err);
            if (callback) callback(err, null);
            return;
        }
        try {
            var result = JSON.parse(body);
            console.log('✅ Actuation successful on mote:', result);
            // Broadcast actuation state to all connected web browser clients
            io.emit('actuation', {
                action: action,
                state: result.state,
                source: source,
                message: 'Executed ' + action.toUpperCase() + ' from ' + source
            });
            if (callback) callback(null, result);
        } catch(e) {
            console.log('⚠️  Raw actuation response from mote:', body);
            if (callback) callback(null, { raw: body });
        }
    });
}

// Local Actuation API (used by the browser UI and curl)
app.get('/api/led/:action', function(req, res) {
    var action = req.params.action.toLowerCase();
    if (['on', 'off', 'toggle'].indexOf(action) === -1) {
        return res.status(400).json({ error: 'Invalid action. Use on, off, or toggle' });
    }
    actuateEdgeDevice(action, 'Web UI / API', function(err, result) {
        if (err) return res.status(500).json({ error: err.message });
        res.json(result);
    });
});

// Status endpoint
app.get('/status', function(req, res){
    res.json({
        targetIp: targetIp,
        thingspeakEnabled: Boolean(thingspeakApiKey),
        talkbackEnabled: Boolean(talkbackId && talkbackApiKey),
        timestamp: new Date().toISOString()
    });
});

io.on('connection', function(socket) {
    console.log('👤 Client connected to local visualization web UI');
});

// ============================================================================
// ThingSpeak Cloud Telemetry Upload
// ============================================================================
function uploadToThingSpeak(apiKey, temp, hum) {
    var tsUrl = 'https://api.thingspeak.com/update';
    request.post({
        url: tsUrl,
        form: {
            api_key: apiKey,
            field1: temp,
            field2: hum
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
// ThingSpeak TalkBack Cloud Actuation Poller
// ============================================================================
function checkTalkBackCommands() {
    if (!talkbackId || !talkbackApiKey) return;

    var talkBackUrl = 'https://api.thingspeak.com/talkbacks/' + talkbackId + '/commands/execute.json?api_key=' + talkbackApiKey;

    request.get({ url: talkBackUrl, timeout: 4000 }, function(err, res, body) {
        if (err || !body || body.trim() === '') return;

        try {
            var data = JSON.parse(body);
            var cmdString = (data.command_string || '').trim().toUpperCase();

            if (!cmdString) return;

            console.log('\n⚡ [ThingSpeak TalkBack] Cloud Command Received: "' + cmdString + '"');

            if (cmdString === 'LED_ON' || cmdString === 'ON' || cmdString === '1') {
                actuateEdgeDevice('on', 'ThingSpeak Cloud (TalkBack)');
            } else if (cmdString === 'LED_OFF' || cmdString === 'OFF' || cmdString === '0') {
                actuateEdgeDevice('off', 'ThingSpeak Cloud (TalkBack)');
            } else if (cmdString === 'LED_TOGGLE' || cmdString === 'TOGGLE') {
                actuateEdgeDevice('toggle', 'ThingSpeak Cloud (TalkBack)');
            } else {
                console.log('⚠️  Unknown TalkBack command string:', cmdString);
            }
        } catch(e) {
            // If body is plain text instead of JSON
            var rawCmd = body.trim().toUpperCase();
            if (rawCmd.indexOf('LED_ON') !== -1 || rawCmd === 'ON') {
                console.log('\n⚡ [ThingSpeak TalkBack] Cloud Command Received: "' + rawCmd + '"');
                actuateEdgeDevice('on', 'ThingSpeak Cloud (TalkBack)');
            } else if (rawCmd.indexOf('LED_OFF') !== -1 || rawCmd === 'OFF') {
                console.log('\n⚡ [ThingSpeak TalkBack] Cloud Command Received: "' + rawCmd + '"');
                actuateEdgeDevice('off', 'ThingSpeak Cloud (TalkBack)');
            } else if (rawCmd.indexOf('LED_TOGGLE') !== -1 || rawCmd === 'TOGGLE') {
                console.log('\n⚡ [ThingSpeak TalkBack] Cloud Command Received: "' + rawCmd + '"');
                actuateEdgeDevice('toggle', 'ThingSpeak Cloud (TalkBack)');
            }
        }
    });
}

// Check for Cloud TalkBack commands every 4 seconds
if (talkbackId && talkbackApiKey) {
    setInterval(checkTalkBackCommands, 4000);
}

// ============================================================================
// Background Telemetry Polling Loop (polls edge device every 3 seconds)
// ============================================================================
setInterval(function () {
    request.get({ url: targetUrl, timeout: 2500 }, function(err, res, body){
        if (err) {
            console.log('⚠️  Polling error from [' + targetIp + ']:', err.message || err);
            return;
        }
        try {
            var obj = JSON.parse(body);
            console.log('📥 Sensor Reading: Temp=' + obj.temp + '°C, Hum=' + obj.hum + '%, LED=' + (obj.led ? 'ON' : 'OFF'));

            // 1. Emit live chart telemetry
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
    console.log('🚀 Local server running on http://localhost:3000');
    console.log('Usage: node index.js [EDGE_IPV6] [THINGSPEAK_KEY] [TALKBACK_ID] [TALKBACK_KEY]\n');
});
