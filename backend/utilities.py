from __future__ import print_function;

import sys;
import time;



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

def filterNone(obj):
	if isinstance(obj, dict):
		return dict((k, filterNone(v)) for k, v in obj.iteritems() if v is not None);
	elif isinstance(obj, list):
		return [filterNone(entry) for entry in obj];
	else:
		return obj;

def getNumValidKeys(obj):
	return len(filter(lambda x: obj[x] is not None, list(obj.keys())));

def encodeUTF8(s):
	if not isinstance(s, str):
		s = strng.encode("utf-8");
	return s;



def ceil(n):											# from https://stackoverflow.com/a/32559239
	res = int(n);
	return res if res == n or n < 0 else res+1;

def floor(n):
	res = int(n);
	return res if res == 0 or n >= 0 else res-1;
