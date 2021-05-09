let _ = require("lodash");
let fs = require("fs");
let path = require("path");
let {StringDecoder} = require("string_decoder");
let express = require("express");
let WebSocket = require("ws");
let app = express();

let {WebSocketClient} = require("./client/js/WebSocketClient.js");
let {BootstrapStep}   = require("./client/js/BootstrapStep.js");



let wss = new WebSocket.Server({ port: 2019 });
console.log("whatsapp-web-reveng API server listening on port 2019");

let backendInfo = {
    url: "ws://localhost:2020",
    timeout: 10000
};

wss.on("connection", function(clientWebsocketRaw, req) {
    let backendWebsocket = new WebSocketClient();
    let clientWebsocket = new WebSocketClient().initializeFromRaw(clientWebsocketRaw, "api2client", {getOnMessageData: msg => new StringDecoder("utf-8").write(msg.data)});
    clientWebsocket.send({ type: "connected" });
    //clientWebsocket.onClose(() => backendWebsocket.disconnect());

    clientWebsocket.waitForMessage({
        condition: obj => obj.from == "client"  &&  obj.type == "call"  &&  obj.command == "api-connectBackend",
        keepWhenHit: true
    }).then(clientCallRequest => {
        if(backendWebsocket.isOpen)
            return;
        new BootstrapStep({
            websocket: backendWebsocket,
            actor: websocket => {
                websocket.initialize(backendInfo.url, "api2backend", {func: WebSocket, args: [{ perMessageDeflate: false }], getOnMessageData: msg => new StringDecoder("utf-8").write(msg.data)});
                websocket.onClose(() => {
                    clientWebsocket.send({ type: "resource_gone", resource: "backend" });
                });
            },
            request: {
                type: "waitForMessage",
                condition: obj => obj.from == "backend"  &&  obj.type == "connected"
            }
        }).run(backendInfo.timeout).then(backendResponse => {
            clientCallRequest.respond({ type: "resource_connected", resource: "backend" });
        }).catch(reason => {
            clientCallRequest.respond({ type: "error", reason: reason });
        });
    }).run();

    clientWebsocket.waitForMessage({
        condition: obj => obj.from == "client"  &&  obj.type == "call"  &&  obj.command == "backend-connectWhatsApp",
        keepWhenHit: true
    }).then(clientCallRequest => {
        if(!backendWebsocket.isOpen) {
            clientCallRequest.respond({ type: "error", reason: "No backend connected." });
            return;
        }
        new BootstrapStep({
            websocket: backendWebsocket,
            request: {
                type: "call",
                callArgs: { command: "backend-connectWhatsApp" },
                successCondition: obj => obj.type == "resource_connected"  &&  obj.resource == "whatsapp"  &&  obj.resource_instance_id
            }
        }).run(backendInfo.timeout).then(backendResponse => {
            backendWebsocket.activeWhatsAppInstanceId = backendResponse.data.resource_instance_id;
            backendWebsocket.waitForMessage({
                condition: obj => obj.type == "resource_gone"  &&  obj.resource == "whatsapp",
                keepWhenHit: false
            }).then(() => {
                delete backendWebsocket.activeWhatsAppInstanceId;
                clientWebsocket.send({ type: "resource_gone", resource: "whatsapp" });
            });
            clientCallRequest.respond({ type: "resource_connected", resource: "whatsapp" });
        }).catch(reason => {
            clientCallRequest.respond({ type: "error", reason: reason });
        });
    }).run();

    clientWebsocket.waitForMessage({
        condition: obj => obj.from == "client"  &&  obj.type == "call"  &&  obj.command == "backend-disconnectWhatsApp",
        keepWhenHit: true
    }).then(clientCallRequest => {
        if(!backendWebsocket.isOpen) {
            clientCallRequest.respond({ type: "error", reason: "No backend connected." });
            return;
        }
        new BootstrapStep({
            websocket: backendWebsocket,
            request: {
                type: "call",
                callArgs: { command: "backend-disconnectWhatsApp", whatsapp_instance_id: backendWebsocket.activeWhatsAppInstanceId },
                successCondition: obj => obj.type == "resource_disconnected"  &&  obj.resource == "whatsapp"  &&  obj.resource_instance_id == backendWebsocket.activeWhatsAppInstanceId
            }
        }).run(backendInfo.timeout).then(backendResponse => {
            clientCallRequest.respond({ type: "resource_disconnected", resource: "whatsapp" });
        }).catch(reason => {
            clientCallRequest.respond({ type: "error", reason: reason });
        });
    }).run();

    clientWebsocket.waitForMessage({
        condition: obj => obj.from == "client"  &&  obj.type == "call"  &&  obj.command == "backend-generateQRCode",
        keepWhenHit: true
    }).then(clientCallRequest => {
        if(!backendWebsocket.isOpen) {
            clientCallRequest.respond({ type: "error", reason: "No backend connected." });
            return;
        }
        new BootstrapStep({
            websocket: backendWebsocket,
            request: {
                type: "call",
                callArgs: { command: "backend-generateQRCode", whatsapp_instance_id: backendWebsocket.activeWhatsAppInstanceId },
                successCondition: obj => obj.from == "backend"  &&  obj.type == "generated_qr_code"  &&  obj.image  &&  obj.content
            }
        }).run(backendInfo.timeout).then(backendResponse => {
            clientCallRequest.respond({ type: "generated_qr_code", image: backendResponse.data.image })

            backendWebsocket.waitForMessage({
                condition: obj => obj.type == "whatsapp_message_received"  &&  obj.message  &&  obj.message_type  &&  obj.timestamp  &&  obj.resource_instance_id == backendWebsocket.activeWhatsAppInstanceId,
                keepWhenHit: true
            }).then(whatsAppMessage => {
                let d = whatsAppMessage.data;
                clientWebsocket.send({ type: "whatsapp_message_received", message: d.message, message_type: d.message_type, timestamp: d.timestamp });
            }).run();
        }).catch(reason => {
            clientCallRequest.respond({ type: "error", reason: reason });
        })
    }).run();
    clientWebsocket.waitForMessage({
        condition: obj => obj.from === "client"  &&  obj.type === "call"  &&  obj.command === "backend-getChatHistory" && "jid" in obj,
        keepWhenHit: true
    }).then(
        clientCallRequest => {
            if(!backendWebsocket.isOpen) {
                clientCallRequest.respond({ type: "error", reason: "No backend connected." });
                return;
            }
            let jid = clientCallRequest.data.jid;
            new BootstrapStep({
                websocket: backendWebsocket,
                request: {
                    type: "call",
                    callArgs: {
                        jid,
                        command: "backend-getChatHistory",
                        whatsapp_instance_id: backendWebsocket.activeWhatsAppInstanceId,
                    },
                    successCondition: obj => "from" in obj && "jid" in obj && "type" in obj &&
                        obj.from === "backend" && obj.jid === jid && obj.type === "chat_history",
                }
            }).run().then(
                backendResponse => clientCallRequest.respond(
                    {
                        type: "chat_history",
                        jid: backendResponse.data.jid,
                        messages: backendResponse.data.content[0][2]
                    }
            ));
        }).run();


    //TODO:
    // - designated backend call function to make everything shorter
    // - allow client to call "backend-getLoginInfo" and "backend-getConnectionInfo"
    // - add buttons for that to client
    // - look for handlers in "decoder.py" and add them to output information
    // - when decoding fails, write packet to file for further investigation later
    // - List contacts and add buttons for each to get messages



    /*let send = (obj, tag) => {
        let msgTag = tag==undefined ? (+new Date()) : tag;
        if(obj.from == undefined)
            obj.from = "api";
        clientWebsocket.send(`${msgTag},${JSON.stringify(obj)}`);
    };

    send({ type: "connected" });*/
    /*let backendCall = command => {
        if(!waBackendValid) {
            send({ type: "error", msg: "No backend connected." });
            return;
        }
        waBackend.onmessage = msg => {
            let data = JSON.parse(msg.data);
            if(data.status == 200)
                send(data);
        };
        waBackend.send(command);
    };*/

    /*clientWebsocket.on("message", function(msg) {
        let tag = msg.split(",")[0];
        let obj = JSON.parse(msg.substr(tag.length + 1));

        switch(obj.command) {
            case "api-connectBackend": {*/


                //backendWebsocket = new WebSocketClient("ws://localhost:2020", true);
                //backendWebsocket.onClose

                /*waBackend = new WebSocket("ws://localhost:2020", { perMessageDeflate: false });
                waBackend.onclose = () => {
                    waBackendValid = false;
                    waBackend = undefined;
                    send({ type: "resource_gone", resource: "backend" });
                };
                waBackend.onopen = () => {
                    waBackendValid = true;
                    send({ type: "resource_connected", resource: "backend" }, tag);
                };*/
                //break;
            //}

            /*case "backend-connectWhatsApp":
            case "backend-generateQRCode": {
                backendCall(msg);
                break;
            }*/
    //	}
    //});

    //clientWebsocket.on("close", function() {
        /*if(waBackend != undefined) {
            waBackend.onclose = () => {};
            waBackend.close();
            waBackend = undefined;
        }*/
    //});
})




app.use(express.static("client"));

app.listen(2018, function() {
    console.log("whatsapp-web-reveng HTTP server listening on port 2018");
});
