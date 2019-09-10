#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys;
sys.dont_write_bytecode = True;

import os;
import signal;
import base64;
from threading import Thread, Timer
import math;
import time;
import datetime;
import json;
import io;
from time import sleep;
from Crypto.Cipher import AES;
from Crypto.Hash import SHA256;
import hashlib;
import hmac;
import traceback;

import websocket;
import curve25519;
import pyqrcode;
from utilities import *;
from whatsapp_binary_reader import whatsappReadBinary;

reload(sys);
sys.setdefaultencoding("utf-8");



def HmacSha256(key, sign):
    return hmac.new(key, sign, hashlib.sha256).digest();

def HKDF(key, length, appInfo=""):						# implements RFC 5869, some parts from https://github.com/MirkoDziadzka/pyhkdf
    key = HmacSha256("\0"*32, key);
    keyStream = "";
    keyBlock = "";
    blockIndex = 1;
    while len(keyStream) < length:
        keyBlock = hmac.new(key, msg=keyBlock+appInfo+chr(blockIndex), digestmod=hashlib.sha256).digest();
        blockIndex += 1;
        keyStream += keyBlock;
    return keyStream[:length];

def AESPad(s):
    bs = AES.block_size;
    return s + (bs - len(s) % bs) * chr(bs - len(s) % bs);

def to_bytes(n, length, endianess='big'):
    h = '%x' % n
    s = ('0'*(len(h) % 2) + h).zfill(length*2).decode('hex')
    return s if endianess == 'big' else s[::-1]

def AESUnpad(s):
    return s[:-ord(s[len(s)-1:])];

def AESEncrypt(key, plaintext):							# like "AESPad"/"AESUnpad" from https://stackoverflow.com/a/21928790
    plaintext = AESPad(plaintext);
    iv = os.urandom(AES.block_size);
    cipher = AES.new(key, AES.MODE_CBC, iv);
    return iv + cipher.encrypt(plaintext);

def WhatsAppEncrypt(encKey, macKey, plaintext):
    enc = AESEncrypt(encKey, plaintext)
    return HmacSha256(macKey, enc) + enc;				# this may need padding to 64 byte boundary

def AESDecrypt(key, ciphertext):						# from https://stackoverflow.com/a/20868265
    iv = ciphertext[:AES.block_size];
    cipher = AES.new(key, AES.MODE_CBC, iv);
    plaintext = cipher.decrypt(ciphertext[AES.block_size:]);
    return AESUnpad(plaintext);



class WhatsAppWebClient:
    websocketIsOpened = False;
    onOpenCallback = None;
    onMessageCallback = None;
    onCloseCallback = None;
    activeWs = None;
    messageSentCount = 0;
    websocketThread = None;
    messageQueue = {};																# maps message tags (provided by WhatsApp) to more information (description and callback)
    loginInfo = {
        "clientId": None,
        "serverRef": None,
        "privateKey": None,
        "publicKey": None,
        "key": {
            "encKey": None,
            "macKey": None
        }
    };
    connInfo = {
        "clientToken": None,
        "serverToken": None,
        "browserToken": None,
        "secret": None,
        "sharedSecret": None,
        "me": None
    };

    def __init__(self, onOpenCallback, onMessageCallback, onCloseCallback):
        self.onOpenCallback = onOpenCallback;
        self.onMessageCallback = onMessageCallback;
        self.onCloseCallback = onCloseCallback;
        websocket.enableTrace(True);
        self.connect();



    def onOpen(self, ws):
        try:
            self.websocketIsOpened = True;
            if self.onOpenCallback is not None and "func" in self.onOpenCallback:
                self.onOpenCallback["func"](self.onOpenCallback);
            eprint("WhatsApp backend Websocket opened.");
        except:
            eprint(traceback.format_exc());

    def onError(self, ws, error):
        eprint(error);

    def onClose(self, ws):
        self.websocketIsOpened = False;
        if self.onCloseCallback is not None and "func" in self.onCloseCallback:
            self.onCloseCallback["func"](self.onCloseCallback);
        eprint("WhatsApp backend Websocket closed.");

    def keepAlive(self):
        if self.activeWs is not None:
            self.activeWs.send("?,,")
            Timer(20.0, self.keepAlive).start()

    def onMessage(self, ws, message):
        try:
            messageSplit = message.split(",", 1);
            messageTag = messageSplit[0];
            messageContent = messageSplit[1];
            
            if messageTag in self.messageQueue:											# when the server responds to a client's message
                pend = self.messageQueue[messageTag];
                if pend["desc"] == "_status":
                    if messageContent[0] == 'Pong' and messageContent[1] == True:
                        pend["callback"]({"Connected": True,"user":self.connInfo["me"],"pushname":self.connInfo["pushname"]})
                elif pend["desc"] == "_restoresession":
                    eprint("")  # TODO implement Challenge Solving
                elif pend["desc"] == "_login":
                    eprint("Message after login: ", message);
                    self.loginInfo["serverRef"] = json.loads(messageContent)["ref"];
                    eprint("set server id: " + self.loginInfo["serverRef"]);
                    self.loginInfo["privateKey"] = curve25519.Private();
                    self.loginInfo["publicKey"] = self.loginInfo["privateKey"].get_public();
                    qrCodeContents = self.loginInfo["serverRef"] + "," + base64.b64encode(self.loginInfo["publicKey"].serialize()) + "," + self.loginInfo["clientId"];
                    eprint("qr code contents: " + qrCodeContents);

                    svgBuffer = io.BytesIO();											# from https://github.com/mnooner256/pyqrcode/issues/39#issuecomment-207621532
                    pyqrcode.create(qrCodeContents, error='L').svg(svgBuffer, scale=6, background="rgba(0,0,0,0.0)", module_color="#122E31", quiet_zone=0);
                    if "callback" in pend and pend["callback"] is not None and "func" in pend["callback"] and pend["callback"]["func"] is not None and "tag" in pend["callback"] and pend["callback"]["tag"] is not None:
                        pend["callback"]["func"]({ "type": "generated_qr_code", "image": "data:image/svg+xml;base64," + base64.b64encode(svgBuffer.getvalue()), "content": qrCodeContents }, pend["callback"]);
            else:
                try:
                    jsonObj = json.loads(messageContent);								# try reading as json
                except ValueError, e:
                    if messageContent != "":
                        hmacValidation = HmacSha256(self.loginInfo["key"]["macKey"], messageContent[32:]);
                        if hmacValidation != messageContent[:32]:
                            raise ValueError("Hmac mismatch");
                        
                        decryptedMessage = AESDecrypt(self.loginInfo["key"]["encKey"], messageContent[32:]);
                        try:
                            processedData = whatsappReadBinary(decryptedMessage, True);
                            messageType = "binary";
                        except:
                            processedData = { "traceback": traceback.format_exc().splitlines() };
                            messageType = "error";
                        finally:
                            self.onMessageCallback["func"](processedData, self.onMessageCallback, { "message_type": messageType });
                else:
                    self.onMessageCallback["func"](jsonObj, self.onMessageCallback, { "message_type": "json" });
                    if isinstance(jsonObj, list) and len(jsonObj) > 0:					# check if the result is an array
                        eprint(json.dumps(jsonObj));
                        if jsonObj[0] == "Conn":
                            Timer(20.0, self.keepAlive).start() # Keepalive Request
                            self.connInfo["clientToken"] = jsonObj[1]["clientToken"];
                            self.connInfo["serverToken"] = jsonObj[1]["serverToken"];
                            self.connInfo["browserToken"] = jsonObj[1]["browserToken"];
                            self.connInfo["me"] = jsonObj[1]["wid"];
                            
                            self.connInfo["secret"] = base64.b64decode(jsonObj[1]["secret"]);
                            self.connInfo["sharedSecret"] = self.loginInfo["privateKey"].get_shared_key(curve25519.Public(self.connInfo["secret"][:32]), lambda a: a);
                            sse = self.connInfo["sharedSecretExpanded"] = HKDF(self.connInfo["sharedSecret"], 80);
                            hmacValidation = HmacSha256(sse[32:64], self.connInfo["secret"][:32] + self.connInfo["secret"][64:]);
                            if hmacValidation != self.connInfo["secret"][32:64]:
                                raise ValueError("Hmac mismatch");

                            keysEncrypted = sse[64:] + self.connInfo["secret"][64:];
                            keysDecrypted = AESDecrypt(sse[:32], keysEncrypted);
                            self.loginInfo["key"]["encKey"] = keysDecrypted[:32];
                            self.loginInfo["key"]["macKey"] = keysDecrypted[32:64];
                            
                            # eprint("private key            : ", base64.b64encode(self.loginInfo["privateKey"].serialize()));
                            # eprint("secret                 : ", base64.b64encode(self.connInfo["secret"]));
                            # eprint("shared secret          : ", base64.b64encode(self.connInfo["sharedSecret"]));
                            # eprint("shared secret expanded : ", base64.b64encode(self.connInfo["sharedSecretExpanded"]));
                            # eprint("hmac validation        : ", base64.b64encode(hmacValidation));
                            # eprint("keys encrypted         : ", base64.b64encode(keysEncrypted));
                            # eprint("keys decrypted         : ", base64.b64encode(keysDecrypted));

                            eprint("set connection info: client, server and browser token; secret, shared secret, enc key, mac key");
                            eprint("logged in as " + jsonObj[1]["pushname"]  + " (" + jsonObj[1]["wid"] + ")");
                        elif jsonObj[0] == "Stream":
                            pass;
                        elif jsonObj[0] == "Props":
                            pass;
        except:
            eprint(traceback.format_exc());



    def connect(self):
        self.activeWs = websocket.WebSocketApp("wss://web.whatsapp.com/ws",
                                               on_message = lambda ws, message: self.onMessage(ws, message),
                                               on_error = lambda ws, error: self.onError(ws, error),
                                               on_open = lambda ws: self.onOpen(ws),
                                               on_close = lambda ws: self.onClose(ws),
                                               header = { "Origin: https://web.whatsapp.com" });
        
        self.websocketThread = Thread(target = self.activeWs.run_forever);
        self.websocketThread.daemon = True;
        self.websocketThread.start();

    def generateQRCode(self, callback=None):
        self.loginInfo["clientId"] = base64.b64encode(os.urandom(16));
        messageTag = str(getTimestamp());
        self.messageQueue[messageTag] = { "desc": "_login", "callback": callback };
        message = messageTag + ',["admin","init",[0,3,2390],["Chromium at ' + datetime.datetime.now().isoformat() + '","Chromium"],"' + self.loginInfo["clientId"] + '",true]';
        self.activeWs.send(message);
        
    def restoreSession(self, callback=None):
        messageTag = str(getTimestamp())
        message = messageTag + ',["admin","init",[0,3,2390],["Chromium at ' + datetime.now().isoformat() + '","Chromium"],"' + self.loginInfo["clientId"] + '",true]'
        self.activeWs.send(message)

        messageTag = str(getTimestamp())
        self.messageQueue[messageTag] = {"desc": "_restoresession"}
        message = messageTag + ',["admin","login","' + self.connInfo["clientToken"] + '", "' + self.connInfo[
            "serverToken"] + '", "' + self.loginInfo["clientId"] + '", "takeover"]'

        self.activeWs.send(message)
        
    def getLoginInfo(self, callback):
        callback["func"]({ "type": "login_info", "data": self.loginInfo }, callback);
    
    def getConnectionInfo(self, callback):
        callback["func"]({ "type": "connection_info", "data": self.connInfo }, callback);
    
    def sendTextMessage(self, number, text):
        messageId = "3EB0"+binascii.hexlify(Random.get_random_bytes(8)).upper()
        messageTag = str(getTimestamp())
        messageParams = {"key": {"fromMe": True, "remoteJid": number + "@s.whatsapp.net", "id": messageId},"messageTimestamp": getTimestamp(), "status": 1, "message": {"conversation": text}}
        msgData = ["action", {"type": "relay", "epoch": str(self.messageSentCount)},[["message", None, WAWebMessageInfo.encode(messageParams)]]]
        encryptedMessage = WhatsAppEncrypt(self.loginInfo["key"]["encKey"], self.loginInfo["key"]["macKey"],whatsappWriteBinary(msgData))
        payload = bytearray(messageId) + bytearray(",") + bytearray(to_bytes(WAMetrics.MESSAGE, 1)) + bytearray([0x80]) + encryptedMessage
        self.messageSentCount = self.messageSentCount + 1
        self.messageQueue[messageId] = {"desc": "__sending"}
        self.activeWs.send(payload, websocket.ABNF.OPCODE_BINARY)
        
    def status(self, callback=None):
        if self.activeWs is not None:
            messageTag = str(getTimestamp())
            self.messageQueue[messageTag] = {"desc": "_status", "callback": callback}
            message = messageTag + ',["admin", "test"]'
            self.activeWs.send(message)

    def disconnect(self):
        self.activeWs.send('goodbye,,["admin","Conn","disconnect"]');		# WhatsApp server closes connection automatically when client wants to disconnect
        #time.sleep(0.5);
        #self.activeWs.close();
