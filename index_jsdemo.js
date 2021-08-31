let WebSocket = require("ws");

let wss = new WebSocket.Server({ port: 2021 });
console.log("whatsapp-web-reveng jsdemo server listening on port 2021");

wss.on("connection", function(ws, req) {
    let whatsapp = new WebSocket("wss://web.whatsapp.com/ws", { headers: { "Origin": "https://web.whatsapp.com" } });
    
    ws.onmessage		= function(e) { whatsapp.send(e.data); }
    ws.onclose			= function(e) { whatsapp.close(); }
    whatsapp.onopen		= function(e) { ws.send("whatsapp_open"); }
    whatsapp.onmessage	= function(e) { ws.send(e.data); }
    whatsapp.onclose	= function(e) { ws.close(); }
});
