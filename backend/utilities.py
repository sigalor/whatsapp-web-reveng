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
