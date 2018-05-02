#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys;
sys.dont_write_bytecode = True;

import os;
import signal;
import base64;

from utilities import *;
import decoder;

reload(sys);
sys.setdefaultencoding("utf-8");



if len(sys.argv) < 2:
	eprint("usage: " + sys.argv[0] + " [base64 string]");
	exit();

decoder.connInfo["me"] = "123456789@c.us";
processedMsgMessage = decoder.MessageParser(base64.b64decode(sys.argv[1])).readMsgMessage();
print json.dumps(processedData, indent=4, ensure_ascii=False, sort_keys=True);
