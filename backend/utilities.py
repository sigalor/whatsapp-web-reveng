from __future__ import print_function;

import sys;
import os;
import time;
import datetime;
import json;
import traceback;
import hashlib;



def eprint(*args, **kwargs):							# from https://stackoverflow.com/a/14981125
	print(*args, file=sys.stderr, **kwargs);

def getTimestamp():
	return int(time.time());

def getTimestampMs():
	return int(round(time.time() * 1000));

def mergeDicts(x, y):									# from https://stackoverflow.com/a/26853961
	if x is None and y is None:
		return;
	z = (y if x is None else x).copy();
	if x is not None and y is not None:
		z.update(y);
	return z;

def getAttr(obj, key, alt=None):
	return obj[key] if isinstance(obj, dict) and key in obj else alt;



def createDirectory(dir):
	if not os.path.exists(dir):
		os.makedirs(dir);

def readJSONFile(filename, alt=None):
	if not os.path.exists(filename):
		return alt;
	with open(filename, "r") as f:
		jsonStr = f.read();
	try:
		jsonObj = json.loads(jsonStr);
	except:
		return alt;
	finally:
		return jsonObj;

def writeJSONFile(filename, obj, pretty=True):
	if not isinstance(obj, dict) and not isinstance(obj, list):
		eprint("object to write to " + filename + " needs to be dict or list");
		return;
	createDirectory(os.path.dirname(filename));
	with open(filename, "w") as f:
		f.write(json.dumps(obj, indent=4, sort_keys=True) if pretty else json.dumps(obj));

def writeMessageToFile(msg, decodable, me, messageTag):
	try:
		currDatetime = datetime.datetime.utcnow();
		messageMD5Sum = hashlib.md5(msg).hexdigest();
		outDirectory = "./backend/%sdecodable_msgs" % ("" if decodable else "un");
		outFilename = currDatetime.strftime("%Y%m%d_%H%M%S") + "_" + messageMD5Sum + ".bin";
		outPath = outDirectory + "/" + outFilename;

		metadataPath = outDirectory + "/metadata.json";
		metadata = readJSONFile(metadataPath, []);
		metadata.append({"filename": outFilename, "time": currDatetime.isoformat() + "Z", "md5": messageMD5Sum, "me": me, "messageTag": messageTag});
		writeJSONFile(metadataPath, metadata);

		createDirectory(outDirectory);
		with open(outPath, "wb") as f:
			f.write(msg);
	except:
		eprint(traceback.format_exc());
	
	return outFilename;
