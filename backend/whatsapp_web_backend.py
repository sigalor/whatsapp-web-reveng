#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function;
import sys;
sys.dont_write_bytecode = True;

import os;
import base64;
import time;
import json;
import uuid;
import traceback;

from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket;
from whatsapp import WhatsAppWebClient;
from utilities import *;

reload(sys);
sys.setdefaultencoding("utf-8");



def eprint(*args, **kwargs):			# from https://stackoverflow.com/a/14981125
    print(*args, file=sys.stderr, **kwargs);



class WhatsAppWeb(WebSocket):
    clientInstances = {};

    def sendJSON(self, obj, tag=None):
        if "from" not in obj:
            obj["from"] = "backend";
        eprint("sending " + json.dumps(obj));
        if tag is None:
            tag = str(getTimestampMs());
        self.sendMessage(tag + "," + json.dumps(obj));

    def sendError(self, reason, tag=None):
        eprint("sending error: " + reason);
        self.sendJSON({ "type": "error", "reason": reason }, tag);

    def handleMessage(self):
        try:
            eprint(self.data);
            tag = self.data.split(",", 1)[0];
            obj = json.loads(self.data[len(tag)+1:]);

            eprint(obj);
            if "from" not in obj or obj["from"] != "api2backend" or "type" not in obj or not (("command" in obj and obj["command"] == "backend-connectWhatsApp") or "whatsapp_instance_id" in obj):
                self.sendError("Invalid request");
                return;

            if obj["type"] == "call":
                if "command" not in obj:
                    self.sendError("Invalid request");
                    return;

                if obj["command"] == "backend-connectWhatsApp":
                    clientInstanceId = uuid.uuid4().hex;
                    onOpenCallback = {
                        "func": lambda cbSelf: self.sendJSON(mergeDicts({ "type": "resource_connected", "resource": "whatsapp" }, getAttr(cbSelf, "args")), getAttr(cbSelf, "tag")),
                        "tag": tag,
                        "args": { "resource_instance_id": clientInstanceId }
                    };
                    onMessageCallback = {
                        "func": lambda obj, cbSelf, moreArgs=None: self.sendJSON(mergeDicts(mergeDicts({ "type": "whatsapp_message_received", "message": obj, "timestamp": getTimestampMs() }, getAttr(cbSelf, "args")), moreArgs), getAttr(cbSelf, "tag")),
                        "args": { "resource_instance_id": clientInstanceId }
                    };
                    onCloseCallback = {
                        "func": lambda cbSelf: self.sendJSON(mergeDicts({ "type": "resource_gone", "resource": "whatsapp" }, getAttr(cbSelf, "args")), getAttr(cbSelf, "tag")),
                        "args": { "resource_instance_id": clientInstanceId }
                    };
                    self.clientInstances[clientInstanceId] = WhatsAppWebClient(onOpenCallback, onMessageCallback, onCloseCallback);
                else:
                    currWhatsAppInstance = self.clientInstances[obj["whatsapp_instance_id"]];
                    callback = {
                        "func": lambda obj, cbSelf: self.sendJSON(mergeDicts(obj, getAttr(cbSelf, "args")), getAttr(cbSelf, "tag")),
                        "tag": tag,
                        "args": { "resource_instance_id": obj["whatsapp_instance_id"] }
                    };
                    if currWhatsAppInstance.activeWs is None:
                        self.sendError("No WhatsApp server connected to backend.");
                        return;

                    cmd = obj["command"];
                    if cmd == "backend-generateQRCode":
                        currWhatsAppInstance.generateQRCode(callback);
                    elif cmd == "backend-restoreSession":
                        currWhatsAppInstance.restoreSession(callback);
                    elif cmd == "backend-getLoginInfo":
                        currWhatsAppInstance.getLoginInfo(callback);
                    elif cmd == "backend-getConnectionInfo":
                        currWhatsAppInstance.getConnectionInfo(callback);
                    elif cmd == "backend-disconnectWhatsApp":
                        currWhatsAppInstance.disconnect();
                        self.sendJSON({ "type": "resource_disconnected", "resource": "whatsapp", "resource_instance_id": obj["whatsapp_instance_id"] }, tag);
        except:
            eprint(traceback.format_exc());

    def handleConnected(self):
        self.sendJSON({ "from": "backend", "type": "connected" });
        eprint(self.address, "connected to backend");

    def handleClose(self):
        whatsapp.disconnect();
        eprint(self.address, "closed connection to backend");

server = SimpleWebSocketServer("", 2020, WhatsAppWeb);
eprint("whatsapp-web-backend listening on port 2020");
server.serveforever();
