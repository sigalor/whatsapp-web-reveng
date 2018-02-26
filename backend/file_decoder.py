#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys;
sys.dont_write_bytecode = True;

import os;
import signal;

from utilities import *;
import decoder;

reload(sys);
sys.setdefaultencoding("utf-8");



if len(sys.argv) < 2:
	eprint("usage: " + sys.argv[0] + " [filename]");
	exit();

if not os.path.exists(sys.argv[1]):
	eprint("input file '" + sys.argv[1] + "' does not exist");
	exit(1);
with open(sys.argv[1], "rb") as f:
	binaryMessage = f.read();

metadataPath = os.path.dirname(sys.argv[1]) + "/metadata.json";
metadata = readJSONFile(metadataPath, []);
if not isinstance(metadata, list):
	eprint("invalid metadata file '" + metadataPath + "'");
	exit(1);
messageMetadata = [a for a in metadata if isinstance(a, dict) and a["filename"]==os.path.basename(sys.argv[1])];
if len(messageMetadata) != 1:
	eprint("no or ambiguous metadata in '" + metadataPath + "' for file '" + sys.argv[1] + "'");
	exit(1);
messageMetadata = messageMetadata[0];
if "me" not in messageMetadata or "messageTag" not in messageMetadata:
	eprint("incomplete metadata in '" + metadataPath + "' for file '" + sys.argv[1] + "'");
	exit(1);

processedData = decoder.processData(messageMetadata["messageTag"], binaryMessage, doFilterNone=False, me=messageMetadata["me"], debug=True);
print json.dumps(processedData, indent=4, sort_keys=True);
