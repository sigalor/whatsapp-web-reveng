#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys;
sys.dont_write_bytecode = True;

import os;
import signal;
import base64;
import math;
import time;
from Crypto.Cipher import AES;
from Crypto.Hash import SHA256;
import hashlib;
import hmac;
import traceback;

import websocket;
import curve25519;
import pyqrcode;
from utilities import *;
import decoder;

reload(sys);
sys.setdefaultencoding("utf-8");



def strToHex(s):
	lst = [];
	for ch in s:
		hv = hex(ord(ch)).replace("0x", "");
		if len(hv) == 1:
			hv = "0" + hv;
		lst.append(hv);
	return reduce(lambda x,y:x+y, lst);



def HmacSha256(key, sign):
	return hmac.new(key, sign, hashlib.sha256).digest();

def HKDF(key, length):									# implements RFC 5869, some parts from https://github.com/MirkoDziadzka/pyhkdf
	keyStream = "";
	keyBlock = "";
	blockIndex = 1;
	while len(keyStream) < length:
		keyBlock = hmac.new(key, msg=keyBlock+chr(blockIndex), digestmod=hashlib.sha256).digest();
		blockIndex += 1;
		keyStream += keyBlock;
	return keyStream[:length];



def AESPad(s):
	bs = AES.block_size;
	print bs, ", ", len(s), ", ", bs - len(s) % bs;
	return s + (bs - len(s) % bs) * chr(bs - len(s) % bs);

def AESUnpad(s):
	return s[:-ord(s[len(s)-1:])];

def AESEncrypt(key, plaintext):							# like "AESPad"/"AESUnpad" from https://stackoverflow.com/a/21928790
	plaintext = AESPad(plaintext);
	iv = "\0"*AES.block_size;	#os.urandom(AES.block_size);
	cipher = AES.new(key, AES.MODE_CBC, iv);
	return iv + cipher.encrypt(plaintext);

def WhatsAppEncrypt(encKey, macKey, plaintext):
	enc = AESEncrypt(encKey, plaintext)
	return enc + HmacSha256(macKey, enc);				# this may need padding to 64 byte boundary

def AESDecrypt(key, ciphertext):						# from https://stackoverflow.com/a/20868265
	iv = ciphertext[:AES.block_size];
	cipher = AES.new(key, AES.MODE_CBC, iv);
	plaintext = cipher.decrypt(ciphertext[AES.block_size:]);
	return AESUnpad(plaintext);



print strToHex(AESEncrypt("Keys"*8, "Hello"));

























