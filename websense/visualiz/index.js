var express = require('express');
var request = require('request');
var mqtt = require('mqtt');
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

// 2. ThingSpeak Configuration (Optional)
var thingspeakApiKey = process.argv[3] || process.env.THINGSPEAK_API_KEY || null;
var talkbackId = process.argv[4] || process.env.TALKBACK_ID || null;
var talkbackApiKey = process.argv[5] || process.env.TALKBACK_API_KEY || null;

// 3. MQTT Broker Configuration (Default: HiveMQ free public broker)
var mqttBrokerUrl = process.env.MQTT_BROKER || 'mqtt://broker.hivemq.com:1883';
var mqttTopicTelemetry = process.env.MQTT_TOPIC_TELEMETRY || 'iot-testbed/nrf52840/telemetry';
var mqttTopicCommand   = process.env.MQTT_TOPIC_COMMAND   || 'iot-testbed/nrf52840/commands';
var mqttTopicStatus    = process.env.MQTT_TOPIC_STATUS     || 'iot-testbed/nrf52840/status';

var lastThingspeakUpload = 0;
var THINGSPEAK_INTERVAL_MS = 15000;

console.log('====================================================');
console.log(' 🌐 IoT Sandbox Gateway — Telemetry & MQTT Actuation');
console.log('====================================================');
console.log('📍 Target Edge Mote URL   :', targetUrl);
console.log('📡 MQTT Broker URL        :', mqttBrokerUrl);
console.log('   • Telemetry Topic     :', mqttTopicTelemetry);
console.log('   • Actuation Topic     :', mqttTopicCommand);
if (thingspeakApiKey) {
    console.log('☁️  ThingSpeak Channel Sync : ENABLED');
}
if (talkbackId && talkbackApiKey) {
    console.log('⚡ ThingSpeak TalkBack Sync : ENABLED');
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
// Actuation Helper Function (Forwards over IPv6 tun0 to Physical Mote)
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
            console.log('✅ Actuation response from mote:', result);
            
            // 1. Broadcast to local Web UI
            io.emit('actuation', {
                action: action,
                state: result.state,
                source: source,
                message: 'Executed ' + action.toUpperCase() + ' via ' + source
            });

            // 2. Publish acknowledgment back to MQTT broker
            if (mqttClient && mqttClient.connected) {
                mqttClient.publish(mqttTopicStatus, JSON.stringify({
                    device: targetIp,
                    action: action,
                    led_state: result.state,
                    source: source,
                    timestamp: new Date().toISOString()
                }));
            }

            if (callback) callback(null, result);
        } catch(e) {
            console.log('⚠️  Raw actuation response:', body);
            if (callback) callback(null, { raw: body });
        }
    });
}

// REST API for browser UI and curl
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

app.get('/status', function(req, res){
    res.json({
        targetIp: targetIp,
        mqttConnected: Boolean(mqttClient && mqttClient.connected),
        mqttBroker: mqttBrokerUrl,
        commandTopic: mqttTopicCommand,
        telemetryTopic: mqttTopicTelemetry,
        timestamp: new Date().toISOString()
    });
});

io.on('connection', function(socket) {
    console.log('👤 Client connected to local visualization web UI');
});

// ============================================================================
// MQTT Client Setup (Real-Time Cloud Actuation & Telemetry)
// ============================================================================
var mqttClient = mqtt.connect(mqttBrokerUrl);

mqttClient.on('connect', function() {
    console.log('📡 [MQTT] Connected to Cloud Broker at', mqttBrokerUrl);
    mqttClient.subscribe(mqttTopicCommand, function(err) {
        if (!err) {
            console.log('⚡ [MQTT] Subscribed to Actuation Topic:', mqttTopicCommand);
            console.log('   (Publish "ON", "OFF", or "TOGGLE" to this topic to control the mote)\n');
        } else {
            console.error('❌ [MQTT] Subscription error:', err);
        }
    });
});

mqttClient.on('message', function(topic, message) {
    var msgStr = message.toString().trim();
    console.log('\n⚡ [MQTT Received] Topic: ' + topic + ' | Payload: "' + msgStr + '"');

    var action = null;
    var upper = msgStr.toUpperCase();

    // Parse plain text: "ON", "OFF", "TOGGLE", "1", "0"
    if (upper === 'ON' || upper === '1' || upper === 'LED_ON') {
        action = 'on';
    } else if (upper === 'OFF' || upper === '0' || upper === 'LED_OFF') {
        action = 'off';
    } else if (upper === 'TOGGLE' || upper === 'LED_TOGGLE') {
        action = 'toggle';
    } else {
        // Try parsing JSON: {"action":"on"} or {"led":"on"}
        try {
            var json = JSON.parse(msgStr);
            var cmd = (json.action || json.command || json.led || '').toLowerCase();
            if (['on', 'off', 'toggle'].indexOf(cmd) !== -1) {
                action = cmd;
            }
        } catch(e) {}
    }

    if (action) {
        actuateEdgeDevice(action, 'MQTT Cloud');
    } else {
        console.warn('⚠️  [MQTT] Unrecognized payload (use ON, OFF, or TOGGLE):', msgStr);
    }
});

mqttClient.on('error', function(err) {
    console.error('❌ [MQTT] Connection error:', err.message || err);
});

// ============================================================================
// ThingSpeak Integration (Optional)
// ============================================================================
function uploadToThingSpeak(apiKey, temp, hum) {
    var tsUrl = 'https://api.thingspeak.com/update';
    request.post({
        url: tsUrl,
        form: { api_key: apiKey, field1: temp, field2: hum },
        timeout: 5000
    }, function(err, res, body) {
        if (!err && res && res.statusCode === 200 && body !== '0') {
            console.log('☁️ [ThingSpeak] Telemetry sent! Entry ID: #' + body.trim());
        }
    });
}

function checkTalkBackCommands() {
    if (!talkbackId || !talkbackApiKey) return;
    var talkBackUrl = 'https://api.thingspeak.com/talkbacks/' + talkbackId + '/commands/execute.json?api_key=' + talkbackApiKey;
    request.get({ url: talkBackUrl, timeout: 4000 }, function(err, res, body) {
        if (err || !body || body.trim() === '') return;
        try {
            var data = JSON.parse(body);
            var cmdString = (data.command_string || '').trim().toUpperCase();
            if (cmdString === 'LED_ON' || cmdString === 'ON') actuateEdgeDevice('on', 'ThingSpeak TalkBack');
            else if (cmdString === 'LED_OFF' || cmdString === 'OFF') actuateEdgeDevice('off', 'ThingSpeak TalkBack');
            else if (cmdString === 'LED_TOGGLE' || cmdString === 'TOGGLE') actuateEdgeDevice('toggle', 'ThingSpeak TalkBack');
        } catch(e) {}
    });
}
if (talkbackId && talkbackApiKey) {
    setInterval(checkTalkBackCommands, 4000);
}

// ============================================================================
// Background Telemetry Polling Loop (every 3 seconds)
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

            // 1. Emit to local browser UI via Socket.io
            io.emit('data', obj.temp);

            // 2. Publish to Cloud MQTT Broker
            if (mqttClient && mqttClient.connected) {
                var payload = JSON.stringify({
                    device_ip: targetIp,
                    temperature: obj.temp,
                    humidity: obj.hum,
                    led_state: obj.led,
                    timestamp: new Date().toISOString()
                });
                mqttClient.publish(mqttTopicTelemetry, payload);
            }

            // 3. Upload to ThingSpeak (if configured, every 15s)
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
    console.log('🚀 Local server running on http://localhost:3000\n');
});
