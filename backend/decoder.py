import sys;
import os;
import base64;
import json;

from utilities import *;

reload(sys);
sys.setdefaultencoding("utf-8");



connInfo = {
	"me": "1234567890@c.us"
};

SingleByteTokens = [None,None,None,"200","400","404","500","501","502","action","add",
					"after","archive","author","available","battery","before","body",
					"broadcast","chat","clear","code","composing","contacts","count",
					"create","debug","delete","demote","duplicate","encoding","error",
					"false","filehash","from","g.us","group","groups_v2","height","id",
					"image","in","index","invis","item","jid","kind","last","leave",
					"live","log","media","message","mimetype","missing","modify","name",
					"notification","notify","out","owner","participant","paused",
					"picture","played","presence","preview","promote","query","raw",
					"read","receipt","received","recipient","recording","relay",
					"remove","response","resume","retry","s.whatsapp.net","seconds",
					"set","size","status","subject","subscribe","t","text","to","true",
					"type","unarchive","unavailable","url","user","value","web","width",
					"mute","read_only","admin","creator","short","update","powersave",
					"checksum","epoch","block","previous","409","replaced","reason",
					"spam","modify_tag","message_info","delivery","emoji","title",
					"description","canonical-url","matched-text","star","unstar",
					"media_key","filename","identity","unread","page","page_count",
					"search","media_message","security","call_log","profile","ciphertext",
					"invite","gif","vcard","frequent","privacy","blacklist","whitelist",
					"verify","location","document","elapsed","revoke_invite","expiration",
					"unsubscribe","disable"];
DoubleByteTokens = [];

class Tags:
	LIST_EMPTY   = 0;
	STREAM_END   = 2;
	DICTIONARY_0 = 236;
	DICTIONARY_1 = 237;
	DICTIONARY_2 = 238;
	DICTIONARY_3 = 239;
	LIST_8       = 248;
	LIST_16      = 249;
	JID_PAIR     = 250;
	HEX_8        = 251;
	BINARY_8     = 252;
	BINARY_20    = 253;
	BINARY_32    = 254;
	NIBBLE_8     = 255;

class MessageParser:
	def __init__(self, data):
		self.data = data;
		self.index = 0;
	
	def checkEOS(self, length):
		if self.index + length > len(self.data):
			raise EOFError("end of stream reached");
	
	def readByte(self):
		self.checkEOS(1);
		ret = ord(self.data[self.index]);
		self.index += 1;
		#print "read byte: " + str(ret);
		return ret;

	def readIntN(self, n, littleEndian=False):
		self.checkEOS(n);
		ret = 0;
		for i in range(n):
			currShift = i if littleEndian else n-1-i;
			ret |= ord(self.data[self.index + i]) << (currShift*8);
		self.index += n;
		return ret;

	def readInt16(self, littleEndian=False):
		return readIntN(2, littleEndian);

	def readInt20(self):
		self.checkEOS(3);
		ret = ((ord(self.data[self.index]) & 15) << 16) + (ord(self.data[self.index+1]) << 8) + ord(self.data[self.index+2]);
		self.index += 3;
		#print "read int20: " + str(ret);
		return ret;

	def readInt32(self, littleEndian=False):
		return readIntN(4, littleEndian);

	def readInt64(self, littleEndian=False):
		return readIntN(8, littleEndian);

	# in the source code, there also is the function "nibblesToBytes". It is the same like this one, but works as if tag==NIBBLE_8
	def readPacked8(self, tag):
		startByte = self.readByte();
		ret = "";
		for i in range(startByte & 127):
			currByte = self.readByte();
			ret += self.unpackByte(tag, (currByte & 0xF0) >> 4) + self.unpackByte(tag, currByte & 0x0F);
		if (startByte >> 7) == 0:
			ret = ret[:len(ret)-1];
		#print "read packed8: " + str(ret);
		return ret;

	def unpackByte(self, tag, value):
		if tag == Tags.NIBBLE_8:
			return self.unpackNibble(value);
		elif tag == Tags.HEX_8:
			return self.unpackHex(value);

	def unpackNibble(self, value):
		if value >= 0 and value <= 9:
			return chr(ord('0') + value);
		elif value == 10:
			return "-";
		elif value == 11:
			return ".";
		elif value == 15:
			return "\0";
		raise ValueError("invalid nibble to unpack: " + value);
	
	def unpackHex(self, value):
		if value < 0 or value > 15:
			raise ValueError("invalid hex to unpack: " + str(value));
		if value < 10:
			return chr(ord('0') + value);
		else:
			return chr(ord('A') + value - 10);
		
	def readVarInt(self):
		self.checkEOS(0);
		startIndex = self.index;
		numBytesLeft = len(self.data) - startIndex;
		currByte = ord(self.data[self.index]);

		# check bounds or var int, upper byte indicates if there are more bytes
		i = 1;
		while i < numBytesLeft and i < 11 and (currByte & 128) != 0:
			currByte = ord(self.data[self.index + i]);
			i += 1;
		if i > 10  or  (i == 10 and ord(self.data[self.index + 9]) > 1):
			raise ValueError("parse error: varint exceeds 64 bits");
		varIntLength = i;
		self.readBytes(i+1 if currByte&128!=0 else i);

		varIntPart1 = 0;
		for i in range(min(3, varIntLength)):
			varIntPart1 |= (ord(self.data[startIndex + i]) & 127) << (i * 7);
		if varIntLength < 4:
			return varIntPart1;

		varIntPart2 = 0;
		for i in range(3, min(6, varIntLength)):
			varIntPart2 |= (ord(self.data[startIndex + i]) & 127) << ((i-3) * 7);
		if varIntLength < 7:
			return (varIntPart2 << 21) | varIntPart1;

		varIntPart3 = 0;
		for i in range(6, min(9, varIntLength)):
			varIntPart3 |= (ord(self.data[startIndex + i]) & 127) << ((i-6) * 7);
		if varIntLength == 10:
			varIntPart3 |= (ord(self.data[startIndex + 9]) & 1) << 21;
		
		ret = ((varIntPart3 << 10 | varIntPart2 >> 11) << 32) | (varIntPart2 << 21 | varIntPart1);
		return ret;

	def readRangedVarInt(self, minVal, maxVal, desc="unknown"):
		ret = self.readVarInt();
		if ret < minVal or ret >= maxVal:
			raise ValueError("varint for " + desc + " is out of bounds: " + str(ret));
		return ret;


	def isListTag(self, tag):
		return tag == Tags.LIST_EMPTY or tag == Tags.LIST_8 or tag == Tags.LIST_16;

	def readListSize(self, tag):
		if(tag == Tags.LIST_EMPTY):
			return 0;
		elif(tag == Tags.LIST_8):
			return self.readByte();
		elif(tag == Tags.LIST_16):
			return self.readInt16();
		raise ValueError("invalid tag for list size: " + str(tag));
	
	def readString(self, tag):
		if tag >= 3 and tag <= 235:
			token = self.getToken(tag);
			if token == "s.whatsapp.net":
				token = "c.us";
			return token;
		
		if tag == Tags.DICTIONARY_0 or tag == Tags.DICTIONARY_1 or tag == Tags.DICTIONARY_2 or tag == Tags.DICTIONARY_3:
			return self.getTokenDouble(tag - Tags.DICTIONARY_0, self.readByte());
		elif tag == Tags.LIST_EMPTY:
			return;
		elif tag == Tags.BINARY_8:
			return self.readStringFromChars(self.readByte());			# is this really "readStringFromChars"? At least seems like that...
		elif tag == Tags.BINARY_20:
			return self.readStringFromChars(self.readInt20());
		elif tag == Tags.BINARY_32:
			return self.readStringFromChars(self.readInt32());
		elif tag == Tags.JID_PAIR:
			i = self.readString(self.readByte());
			j = self.readString(self.readByte());
			if i is None or j is None:
				raise ValueError("invalid jid pair: " + str(i) + ", " + str(j));
			return i + "@" + j;
		elif tag == Tags.NIBBLE_8 or tag == Tags.HEX_8:
			return self.readPacked8(tag);
		else:
			raise ValueError("invalid string with tag " + str(tag));
	
	def readStringFromChars(self, length):		# TODO: investigate app***:2094
		self.checkEOS(length);
		ret = self.data[self.index:self.index+length];
		self.index += length;
		return ret;
	
	def readAttributes(self, n):
		ret = {};
		if n == 0:
			return;
		for i in range(n):
			index = self.readString(self.readByte());
			ret[index] = self.readString(self.readByte());
		return ret;

	def readList(self, tag):
		ret = [];
		for i in range(self.readListSize(tag)):
			ret.append(self.readNode());
		return ret;

	def readNode(self):
		#print base64.b64encode(self.data);
		listSize = self.readListSize(self.readByte());
		descrTag = self.readByte();
		if descrTag == Tags.STREAM_END:
			raise ValueError("unexpected stream end");
		descr = self.readString(descrTag);
		if listSize == 0 or not descr:
			raise ValueError("invalid node");
		#print listSize, listSize-2 + listSize%2 >> 1;
		attrs = self.readAttributes((listSize-1) >> 1);		#self.readAttributes(listSize-2 + listSize%2 >> 1);
		if listSize % 2 == 1:
			return [descr, attrs, None];

		tag = self.readByte();
		print "node content tag is", tag;
		if self.isListTag(tag):
			content = self.readList(tag);
		elif tag == Tags.BINARY_8:
			content = self.readBytes(self.readByte());
		elif tag == Tags.BINARY_20:
			content = self.readBytes(self.readInt20());
		elif tag == Tags.BINARY_32:
			content = self.readBytes(self.readInt32());
		else:
			content = self.readString(tag);
		return [descr, attrs, content];

	def readBytes(self, n):
		ret = "";
		for i in range(n):
			ret += chr(self.readByte());
		return ret;
	
	def getToken(self, index):
		if index < 3 or index >= len(SingleByteTokens):
			raise ValueError("invalid token index: " + str(index));
		return SingleByteTokens[index];

	def getTokenDouble(self, index1, index2):
		n = 256 * index1 + index2;
		if n < 0 or n >= len(DoubleByteTokens):
			raise ValueError("invalid token index: " + str(n));
		return DoubleByteTokens[n];



	def readMsgMessage(self, msgMessageType="__messageFrame"):
		# all definitions seem to be from app***:49974
		# TODO: all other message type and order them!
		if msgMessageType == "__messageFrame":
			names = ["key","message","messageTimestamp","status","participant","ignore","starred","broadcast","pushName","mediaCiphertextSha256","multicast","urlText","urlNumber","messageStubType","clearMedia","messageStubParameters","duration"];
			fields = [1,2,3,4,5,16,17,18,19,20,21,22,23,24,25,26,27];
			types = [270,14,4,8,12,7,7,7,12,13,7,7,7,8,7,76,3];
		elif msgMessageType == "key":
			names = ["remoteJid","fromMe","id","participant"];
			fields = [1,2,3,4];
			types = [12,7,12,12];
		elif msgMessageType == "message":
			names = ["conversation","senderKeyDistributionMessage","imageMessage","contactMessage","locationMessage","extendedTextMessage","documentMessage","audioMessage","videoMessage","call","chat","protocolMessage","contactsArrayMessage","highlyStructuredMessage","fastRatchetKeySenderKeyDistributionMessage","sendPaymentMessage","requestPaymentMessage","liveLocationMessage","stickerMessage"];
			fields = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19];
			types = [12,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14];
		elif msgMessageType == "imageMessage":
			names = ["url","mimetype","caption","fileSha256","fileLength","height","width","mediaKey","fileEncSha256","interactiveAnnotations","directPath","jpegThumbnail","contextInfo","firstScanSidecar","firstScanLength"];
			fields = [1,2,3,4,5,6,7,8,9,10,11,16,17,18,19];
			types = [12,12,12,13,4,3,3,13,13,78,12,13,14,13,3];
		elif msgMessageType == "audioMessage":
			names = ["url","mimetype","fileSha256","fileLength","seconds","ptt","mediaKey","fileEncSha256","directPath","contextInfo","streamingSidecar"];
			fields = [1,2,3,4,5,6,7,8,9,17,18];
			types = [12,12,13,4,3,7,13,13,12,14,13];
		elif msgMessageType == "extendedTextMessage":
			names = ["text","matchedText","canonicalUrl","description","title","textArgb","backgroundArgb","font","jpegThumbnail","contextInfo"];
			fields = [1,2,4,5,6,7,8,9,16,17];
			types = [12,12,12,12,12,15,15,8,13,14];
		elif msgMessageType == "contextInfo":
			names = ["stanzaId","participant","quotedMessage","remoteJid","mentionedJid","conversionSource","conversionData","conversionDelaySeconds","forwardingScore"];
			fields = [1,2,3,4,15,18,19,20,21];
			types = [12,12,14,12,76,12,13,3,3];
		elif msgMessageType == "quotedMessage":
			names = ["conversation","senderKeyDistributionMessage","imageMessage","contactMessage","locationMessage","extendedTextMessage","documentMessage","audioMessage","videoMessage","call","chat","protocolMessage","contactsArrayMessage","highlyStructuredMessage","fastRatchetKeySenderKeyDistributionMessage","sendPaymentMessage","requestPaymentMessage","liveLocationMessage","stickerMessage"];
			fields = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19];
			types = [12,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14];
		elif msgMessageType == "videoMessage":
			names = ["url","mimetype","fileSha256","fileLength","seconds","mediaKey","caption","gifPlayback","height","width","fileEncSha256","interactiveAnnotations","directPath","jpegThumbnail","contextInfo","streamingSidecar","gifAttribution"];
			fields = [1,2,3,4,5,6,7,8,9,10,11,12,13,16,17,18,19];
			types = [12,12,13,4,3,13,12,7,3,3,13,78,12,13,14,13,8];
		elif msgMessageType == "documentMessage":
			names = ["url","mimetype","title","fileSha256","fileLength","pageCount","mediaKey","fileName","fileEncSha256","directPath","jpegThumbnail","contextInfo"];
			fields = [1,2,3,4,5,6,7,8,9,10,16,17];
			types = [12,12,12,13,4,3,13,12,13,12,13,14];
		else:
			# when you encounter an unknown msg message type, look at app***:21326 (with "g = a.oneofToFields" and "f = a.fieldToOneof")
			# set the following breakpoint condition on "t = a.names": (window.currA = a)  &&  false
			# also set a breakpoint at the corresponding parser function (e.g. "parseDocumentMessageProto")
			# when the breakpoint there is hit, just output window.currA and acquire all necessary information
			raise ValueError("unknown msg message type: " + msgMessageType);
		ret = {};

		#print msgMessageType
		for name in names:
			ret[name] = None;
		if msgMessageType == "__messageFrame":
			ret["messageStubParameters"] = [];
			ret["status"] = 1;

		currField = fields[0];
		currFieldIndex = 0;
		while self.index < len(self.data):
			fieldAndEncType = self.readRangedVarInt(0, 1<<32, "field and enc type");
			l = fieldAndEncType & 7;
			wantedField = fieldAndEncType >> 3;
			if wantedField != currField:
				currFieldIndex = fields.index(wantedField) if wantedField in fields else currFieldIndex
				currField = fields[currFieldIndex];
			
			if wantedField == currField:
				def checkType(type):
					if (type & 128) != 0:
						return 2;
					n = type & 31;
					return 0 if n <= 8 else (1 if n <= 11 else (2 if n <= 14 else 5));

				currType = types[currFieldIndex];
				currName = names[currFieldIndex];
				if l != checkType(currType):
					raise ValueError("format error: " + currName + " encoded with wire type " + str(l));
				
				a = currType & 31;
				#g = meta[currFieldIndex];
				if currType & 128 != 0:
					numBytes = self.readVarInt();			# b
					currData = self.readBytes(numBytes);	# h
					while self.index < len(self.data):
						pass;	# TODO (app***:18782)
						#b = self.readVarInt
				elif a == 14:
					numBytes = self.readVarInt();			# w
					currData = self.readBytes(numBytes);	# y
					if currType & 64 != 0:
						pass;	# TODO (app***:18789)
					else:
						encapsMsg = MessageParser(currData).readMsgMessage(currName);
						if currType & 64 != 0:
							ret[currName].append(encapsMsg);
						else:
							ret[currName] = encapsMsg;
				else:
					if a == 1:
						j = self.readRangedVarInt(-(1<<31), 1<<31);
					elif a == 2:
						j = self.readVarInt();
					elif a == 3:
						j = self.readRangedVarInt(0, 1<<32);
					elif a == 4:
						j = self.readRangedVarInt(0, float("inf"));
					elif a == 5:
						i = self.readRangedVarInt(0, 1<<32);
						j = ((-(i>>1)) if i!=0 else i>>1) & 1;
					elif a == 6:
						tmp1 = self.readVarInt();
						tmp2 = tmp1 / 2;
						j = tmp2 if tmp2*2==tmp1 else -tmp2;
					elif a == 7:
						j = bool(self.readRangedVarInt(0, 2));
					elif a == 8:
						j = self.readVarInt();
					elif a == 9:
						j = self.readInt64();	# should be uint64
					elif a == 10:
						j = self.readInt64();
					elif a == 11:
						j = self.readFloat64();
					elif a == 12:
						j = self.readStringFromChars(self.readVarInt());
					elif a == 13:
						j = self.readBytes(self.readVarInt());
					elif a == 15:
						j = self.readInt32();	# should be uint32
					elif a == 16:
						j = self.readInt32();
					elif a == 17:
						j = self.readFloat32();		# TODO (incl. all of the above): Little or Big Endian?
					
					if a != 8:
						if currType & 64 != 0:
							ret[currName].append(j);
						else:
							ret[currName] = j;
				
				#if ret[currName] is not None:
				#	print "WARNING in readMsgMessage: ignored special case with fieldToOneof";
				#	pass;		# TODO: involves something with fieldToOneof (app***:18799), although it seems like that's always undefined...
			
			elif l == 0:
				self.readVarInt();
			elif l == 1:
				self.checkEOS(8);
				self.index += 8;
			elif l == 2:
				advance = self.readVarInt();
				self.checkEOS(advance);
				self.index += advance;
			elif l == 5:
				self.checkEOS(4);
				self.index += 4;


		return ret;
		



def getProperty(node, index, alt):
	return alt if index < 0 or index >= 3 or not isinstance(node, list) or len(node) != 3 or node[index] is None else node[index];

def getTag(node):
	return getProperty(node, 0, None);

def getAttrs(node):
	return getProperty(node, 1, {});

def getChildren(node):
	return getProperty(node, 2, []);


def hasAttr(attrs, key):
	return isinstance(attrs, dict) and key in attrs;

def getAttr(attrs, key, alt=None):
	return attrs[key] if isinstance(attrs, dict) and key in attrs else alt;

def getAttrBase64(attrs, key, alt=None):
	return base64.b64encode(attrs[key]) if isinstance(attrs, dict) and key in attrs and attrs[key] is not None else alt;

def getAttrStr(attrs, key, alt=None):
	return str(attrs[key]) if isinstance(attrs, dict) and key in attrs and attrs[key] is not None else alt;

def getAttrInt(attrs, key, alt=None):
	return safeParseInt(getAttr(attrs, key), alt);

def getAttrOrElse(attrs, key, alt):
	attr = getAttr(attrs, key);
	return attr if bool(attr) else alt;

def getFirstValidAttr(attrs, keys, alt=None):
	if isinstance(attrs, dict) and keys is not None:
		for key in keys:
			if key in attrs:
				return attrs[key];
	return alt;

def findTagInArray(arr, tag, alt=None):
	if not isinstance(arr, list):
		return alt;
	for entry in arr:
		if isinstance(entry, list) and len(entry) == 3 and entry[0] == tag:
			return e;
	return alt;

def appendToSubarray(arr, key, val):
	if key not in arr:
		arr[key] = [];
	arr[key].append(val);

def filterNone(obj):		# partly from https://stackoverflow.com/a/12118700
	if isinstance(obj, dict):
		return dict((k, filterNone(v)) for k, v in obj.iteritems() if v is not None);
	elif isinstance(obj, list):
		return [filterNone(entry) for entry in obj];
	else:
		return obj;

	#return dict((k, filterNone(v) if isinstance(v, dict) else ([filterNone(e) for e in v] if isinstance(v, list) else v)) for k, v in obj.iteritems() if v is not None) if isinstance(obj, dict) else obj;



def actionGetMeta(node):
	actionGetMeta.ret = {};
	if node[0] != "action":
		return actionGetMeta.ret;
	attrs = getAttrs(node);

	addVal = getAttr(attrs, "add");
	missingVal = getAttr(attrs, "missing");
	checksumVal = getAttr(attrs, "checksum");

	def addVal_after_before_last():
		actionGetMeta.ret["pendingMsgsDone"] = (getAttr(attrs, "last") == "true");
		actionGetMeta.ret["resume"] = (getAttr(attrs, "resume") == "true");
	
	def addVal_relay_update():
		actionGetMeta.ret["add"] = addVal;

	if addVal == "unread":
		actionGetMeta.ret["unreadId"] = getAttr(attrs, "index");
		actionGetMeta.ret["unreadFromMe"] = (getAttr(attrs, "owner") == "true");
		actionGetMeta.ret["unreadParticipant"] = getAttr(attrs, "participant");
		addVal_after_before_last();
		addVal_relay_update();
	elif addVal == "after" or addVal == "before" or addVal == "last":
		addVal_after_before_last();
		addVal_relay_update();
	elif addVal == "relay" or addVal == "update":
		addVal_relay_update();
	
	if missingVal == "remove":
		actionGetMeta.ret["missing"] = missingVal;
	if checksumVal is not None and len(checksumVal) != 0:
		actionGetMeta.ret["checksum"] = checksumVal;

	return actionGetMeta.ret;

def groupActionsByType(actions):
	ret = {};
	if not isinstance(actions, list):
		return ret;

	for currAction in actions:
		tag = currAction[0];
		attrs = getAttrs(currAction);
		if tag == "broadcast":
			type = getAttr(attrs, "type");
			if type == "create" or type == "add" or type == "remove":
				appendToSubarray(ret, "msg", currAction);
			elif type == "modify":
				appendToSubarray(ret, "bcUpdate", currAction);
		elif tag == "message" or tag == "groups_v2" or tag == "notification" or tag == "call_log" or tag == "security":
			appendToSubarray(ret, "msg", currAction);
		elif tag == "read" or tag == "log" or tag == "identity":
			appendToSubarray(ret, "cmd", currAction);
		elif tag == "received":
			appendToSubarray(ret, "ack", currAction);
		elif tag == "user":
			appendToSubarray(ret, "contact", currAction);
		elif tag == "contacts":
			appendToSubarray(ret, "contacts", currAction);
		elif tag == "chat":
			type = attrs["type"];
			if type == "mute":
				appendToSubarray(ret, "mute", currAction);
			else:
				appendToSubarray(ret, "chat", currAction);
		elif tag == "battery":
			appendToSubarray(ret, "battery", currAction);
		elif tag == "status":
			appendToSubarray(ret, "status", currAction);
		elif tag == "location":
			appendToSubarray(ret, "location", currAction);
		else:
			raise ValueError("unknown action tag: " + tag);
	
	return ret;




def decodeJid(jid):
	if jid is not None:
		return jid.replace("@s.whatsapp.net", "@c.us");
	return None;

def decodeUrl(url):
	if url is not None and "/u/" not in url:
		return url;
	return None;

#def encodeBytes(bytes):			# is called "decodeBytes" in JavaScript code!
#	return "" if bytes is None else base64.b64encode(bytes);


def isGroup(jid):
	return "g.us" in jid;

def isBroadcast(jid):
	return "broadcast" in jid;

def dropIfConditionMet(conditions, obj):
	return None if True in conditions else obj;

def safeParseInt(val, alt=None):
	if val is None:
		return alt;
	try:
		return int(val);
	except ValueError:
		return alt;

def createWebMessageInfoMsgKey(obj):
	if obj is None:
		raise ValueError("MsgKey error: obj is None");
	usesConstr1 = isinstance(getAttr(obj, "from"), basestring) and isinstance(getAttr(obj, "to"), basestring) and isinstance(getAttr(obj, "id"), basestring);
	usesConstr2 = isinstance(getAttr(obj, "fromMe"), bool) and isinstance(getAttr(obj, "remote"), basestring) and isinstance(getAttr(obj, "id"), basestring);
	if connInfo["me"] is None or len(connInfo["me"]) == 0:
		raise ValueError("MsgKey error: connInfo.me is undefined");
	if usesConstr1 and usesConstr2:
		raise ValueError("MsgKey error: unclear which constructor to use");
	if not usesConstr1 and not usesConstr2:
		raise ValueError("MsgKey error: don't have a matching constructor");
	
	ret = {};
	inOutState = None;
	if usesConstr1:
		selfDir = obj["selfDir"] if obj["from"] == obj["to"] else None;
		if obj["from"] == obj["to"] and obj["from"] == connInfo["me"]:
			fromMe = (selfDir == "out");
			remote = connInfo["me"];
		elif obj["from"] == connInfo["me"]:
			fromMe = True;
			remote = obj["to"];
		elif obj["to"] == connInfo["me"]:
			fromMe = False;
			remote = obj["from"];
		elif obj["from"] == obj["to"] and (isGroup(obj["from"]) or isBroadcast(obj["from"])):
			fromMe = True;
			remote = obj["from"];
		else:
			raise ValueError("MsgKey case error");
		ret["fromMe"] = fromMe;
		ret["remote"] = remote;
		ret["id"] = obj["id"];

	elif usesConstr2:
		if obj["remote"] == connInfo["me"]:
			inOutState = "out" if obj["fromMe"] else "in";
		ret["fromMe"] = obj["fromMe"];
		ret["remote"] = obj["remote"];
		ret["id"] = obj["id"];
	
	if inOutState is not None:
		ret["self"] = inOutState;
	if "participant" in obj:	# TODO: check "d.supportsFeature(d.F.KEY_PARTICIPANT)" (app***:9466)
		ret["participant"] = obj["participant"];
	
	return ret;

def parseConversationProto(info, obj):
	info["type"] = "chat";
	info["body"] = obj;

# all the following from app2***:5407
def parseImageMessageProto(info, obj):
	info["type"] = "image";
	info["clientUrl"] = decodeUrl(getAttr(obj, "url"));
	info["directPath"] = getAttr(obj, "directPath");
	info["mimetype"] = getAttr(obj, "mimetype");
	info["caption"] = getAttr(obj, "caption");
	info["filehash"] = getAttrBase64(obj, "fileSha256", "");
	info["size"] = getAttr(obj, "fileLength");
	info["height"] = getAttr(obj, "height");
	info["width"] = getAttr(obj, "width");
	info["mediaKey"] = getAttrBase64(obj, "mediaKey", "");
	info["body"] = getAttrBase64(obj, "jpegThumbnail", "");

def parseContactMessageProto(info, obj):
	info["type"] = "vcard";
	info["subtype"] = getAttr(obj, "displayName");
	info["body"] = getAttr(obj, "vcard");

def parseContactsArrayMessageProto(info, obj):
	cont = getAttr(obj, "contacts");
	info["type"] = "multi_vcard";
	info["subtype"] = getAttr(obj, "displayName");
	info["vcardList"] = []
	if isinstance(cont, list):
		for c in cont:
			info["vcardList"].append({ "displayName": c["displayName"], "vcard": c["vcard"] });

def parseLocationMessageProto(info, obj):
	name = getAttr(obj, "name");
	address = getAttr(obj, "address");
	info["type"] = "location";
	info["lat"] = getAttrStr(obj, "degreesLatitude");
	info["lng"] = getAttrStr(obj, "degreesLongitude");
	if name is not None and address is not None:
		info["loc"] = str(name) + "\n" + str(address);
	else:
		info["loc"] = getFirstValidAttr(obj, ["name", "address"], "");
	info["body"] = getAttrBase64(obj, "jpegThumbnail", "");
	info["clientUrl"] = getAttr(obj, "clientUrl");

def parseLiveLocationMessageProto(info, obj):
	info["type"] = "location";
	info["isLive"] = True;
	info["lat"] = getAttrStr(obj, "degreesLatitude");
	info["lng"] = getAttrStr(obj, "degreesLongitude");
	info["body"] = getAttrBase64(obj, "jpegThumbnail", "");
	info["accuracy"] = getAttr(obj, "accuracyInMeters");
	info["speed"] = getAttr(obj, "speedInMps");
	info["degrees"] = getAttr(obj, "degreesClockwiseFromMagneticNorth");
	info["comment"] = getAttr(obj, "caption");
	info["sequence"] = getAttr(obj, "sequenceNumber");

def parseExtendedTextMessageProto(info, obj):
	info["type"] = "chat";
	info["subtype"] = "url" if getFirstValidAttr(obj, ["matchedText", "canonicalUrl", "description", "title"]) is not None else None;
	info["body"] = getAttr(obj, "text", "");
	info["matchedText"] = getAttr(obj, "matchedText");
	info["canonicalUrl"] = getAttr(obj, "canonicalUrl");
	info["description"] = getAttr(obj, "description");
	info["title"] = getAttr(obj, "title");
	info["thumbnail"] = getAttrBase64(obj, "jpegThumbnail", "");
	info["textColor"] = getAttr(obj, "textArgb");
	info["backgroundColor"] = getAttr(obj, "backgroundArgb");
	font = getAttr(obj, "font");
	if font >= 0 and font <= 5:		# 0 = SANS_SERIF, 1 = SERIF, 2 = NORICAN_REGULAR, 3 = BRYNDAN_WRITE, 4 = BEBASNEUE_REGULAR, 5 = OSWALD_HEAVY
		info["font"] = font;

def parseDocumentMessageProto(info, obj):
	info["type"] = "document";
	info["clientUrl"] = decodeUrl(getAttr(obj, "url"));
	info["directPath"] = getAttr(obj, "directPath");
	info["mimetype"] = getAttr(obj, "mimetype");
	info["caption"] = getAttr(obj, "title");
	info["filehash"] = getAttrBase64(obj, "fileSha256");
	info["size"] = getAttr(obj, "fileLength", 0);
	info["pageCount"] = getAttr(obj, "pageCount", 0);
	info["mediaKey"] = getAttrBase64(obj, "mediaKey");
	info["filename"] = getAttr(obj, "fileName");
	info["body"] = getAttrBase64(obj, "jpegThumbnail", "");

def parseAudioMessageProto(info, obj):
	info["type"] = "ptt" if getAttr(obj, "ptt") else "audio";
	info["clientUrl"] = decodeUrl(getAttr(obj, "url"));
	info["directPath"] = getAttr(obj, "directPath");
	info["mimetype"] = getAttr(obj, "mimetype");
	info["filehash"] = getAttrBase64(obj, "fileSha256");
	info["size"] = getAttr(obj, "fileLength", 0);
	info["duration"] = str(getAttr(obj, "seconds", 0));
	info["mediaKey"] = getAttrBase64(obj, "mediaKey");
	info["streamingSidecar"] = getAttr(obj, "streamingSidecar");

def parseVideoMessageProto(info, obj):
	info["type"] = "video";
	info["clientUrl"] = decodeUrl(getAttr(obj, "url"));
	info["directPath"] = getAttr(obj, "directPath");
	info["mimetype"] = getAttr(obj, "mimetype");
	info["filehash"] = getAttrBase64(obj, "fileSha256");
	info["size"] = getAttr(obj, "fileLength", 0);
	info["height"] = getAttr(obj, "height");
	info["width"] = getAttr(obj, "width");
	info["duration"] = str(getAttr(obj, "seconds", 0));
	info["mediaKey"] = getAttrBase64(obj, "mediaKey");
	info["caption"] = getAttr(obj, "caption");
	info["body"] = getAttrBase64(obj, "jpegThumbnail", "");
	info["isGif"] = getAttr(obj, "gifPlayback");
	info["gifAttribution"] = getAttr(obj, "gifAttribution");
	info["streamingSidecar"] = getAttr(obj, "streamingSidecar");

def parseProtocolMessageProto(info, obj, tag):
	if tag == "relay":
		key = getAttr(obj, "key");
		if "type" not in info:
			info["type"] = "protocol";
		if "subtype" not in info:
			info["subtype"] = "unknown";
		info["protocolMessageKey"] = {			# TODO: this is probably incomplete (the original code wraps this object in a function)!
			"fromMe": getAttr(obj, "fromMe"),
			"remote": decodeJid(getAttr(obj, "removeJid")),
			"id": getAttr(obj, "id"),
			"participant": decodeJid(getAttr(obj, "participant"))
		};

def parseContextInfoProto(info, obj):
	quotedMessage = getAttr(obj, "quotedMessage");
	mentionedJid = getAttr(obj, "mentionedJid");
	info["quotedMsg"] = parseMsgProto(quotedMessage, {}, None) if quotedMessage else None;
	info["quotedStanzaID"] = getAttr(obj, "stanzaId");
	info["quotedParticipant"] = decodeJid(getAttr(obj, "participant"));
	info["quotedRemoteJid"] = decodeJid(getAttr(obj, "remoteJid"));
	if isinstance(mentionedJid, list):
		info["mentionedJidList"] = [];
		for jid in mentionedJid:
			info["mentionedJidList"].append(decodeJid(jid));
	else:
		info["mentionedJidList"] = mentionedJid;

def parseMsgProto(msg, info, tag):
	print msg, info, tag;
	if msg is None:
		raise ValueError("drop: not Message");
	
	contextInfo = None;
	if isinstance(getAttr(msg, "conversation"), basestring):
		parseConversationProto(info, msg["conversation"]);

	for i in [
		("imageMessage", parseImageMessageProto),
		("contactMessage", parseContactMessageProto),
		("contactsArrayMessage", parseContactsArrayMessageProto),
		("locationMessage", parseLocationMessageProto),
		("liveLocationMessage", parseLiveLocationMessageProto),
		("extendedTextMessage", parseExtendedTextMessageProto),
		("documentMessage", parseDocumentMessageProto),
		("audioMessage", parseAudioMessageProto),
		("videoMessage", parseVideoMessageProto)
	]:
		if i[0] in msg and msg[i[0]] is not None:
			i[1](info, msg[i[0]]);
			contextInfo = getAttr(msg[i[0]], "contextInfo");

	if "protocolMessage" in msg:
		parseProtocolMessageProto(info, msg["protocolMessage"], tag);
	if contextInfo is not None:
		parseContextInfoProto(info, contextInfo);
	
	return info;

def parseWebMessageInfo(msg, tag):
	print msg
	currJid = decodeJid(msg["key"]["remoteJid"]);
	toUser = currJid if msg["key"]["fromMe"] else connInfo["me"];
	fromUser = connInfo["me"] if msg["key"]["fromMe"] else currJid;
	participant = decodeJid(msg["key"]["participant"] if "participant" in msg["key"] else None);
	inOutState = None;
	if currJid == connInfo["me"]:
		inOutState = "out" if msg["key"]["fromMe"] else "in";
	
	if toUser == "broadcast":
		raise ValueError("drop: broadcast");
	msgKey = createWebMessageInfoMsgKey({
		"fromMe": msg["key"]["fromMe"],
		"remote": currJid,
		"id": msg["key"]["id"],
		"participant": participant
	});

	return parseMsgProto(msg["message"], {
		"id": msgKey,
		"from": fromUser,
		"to": toUser,
		"self": inOutState,
		"participant": participant,
		"type": "unknown",
		"t": msg["messageTimestamp"] if "messageTimestamp" in msg else 0,
		"ack": 1 if tag == "fresh" else getAttr(msg, "status") - 1,
		"author": decodeJid(getAttr(msg, "participant")),
		"invis": bool(getAttr(msg, "ignore")),
		"star": bool(getAttr(msg, "starred")),
		"broadcast": bool(msg["key"]["fromMe"] and getAttr(msg, "broadcast")),
		"notifyName": msg["pushName"] if "pushName" in msg else "",
		"encFilehash": getAttrBase64(msg, "mediaCiphertextSha256")
	}, tag);
	

def parseMsgMessage(msg, tag):
	if len(msg) != 3 or msg[0] != "message":
		raise ValueError("invalid msg message");
	currMsg = MessageParser(msg[2]).readMsgMessage();
	return parseWebMessageInfo(currMsg, tag);

def parseMsgGp2(msg):
	if len(msg) != 3 or msg[0] != "groups_v2":
		raise ValueError("invalid gp2 message");
	attrs = getAttrs(msg);
	timestamp = int(getAttr(attrs, "t")) if hasAttr(attrs, "t") else 0;
	id = getAttr(attrs, "id");
	jid = getAttr(attrs, "jid");
	isInvis = getAttr(attrs, "web") == "invis";
	isOwner = getAttr(attrs, "owner") == "true";
	type = getAttr(attrs, "type");
	author = getAttr(attrs, "author");
	participant = getAttr(attrs, "participant");
	typeAttr = None;
	recipients = [];

	if type == "create":
		typeAttr = getAttr(attrs, "subject");
	elif type == "subject":
		typeAttr = getAttr(attrs, "subject");
	elif type == "picture":
		typeAttr = getAttr(attrs, "picture");
	
	if isinstance(msg[2], list):
		for participant in msg[2]:
			if len(participant) != 3:
				continue;
			participantJid = getAttr(participant[1], "jid");
			if participant[0] == "participant" and participantJid is not None:
				recipients.append(participantJid);
	
	msgKey = createWebMessageInfoMsgKey({
		"fromMe": isOwner,
		"remote": jid,
		"id": id,
		"participant": participant
	});
	ret = {
		"t": timestamp,
		"id": msgKey,
		"from": connInfo["me"] if isOwner else jid,
		"to": jid if isOwner else connInfo["me"],
		"author": author,
		"participant": participant,
		"body": str(typeAttr) if typeAttr is not None else None,
		"type": "gp2",
		"subtype": type,
		"invis": isInvis,
		"recipients": recipients
	};
	return dropIfConditionMet([
		not bool(id), not bool(timestamp),
		type not in ["subject", "add", "invite", "remove", "leave", "picture", "modify", "create", "delete", "promote", "demote", "revoke_invite"],
		type == "subject" and not bool(typeAttr),
		type in ["add", "invite", "remove", "leave", "promote", "demote", "modify"] and len(recipients) == 0,
		not bool(jid),
		isinstance(jid, basestring) and jid.split("@")[1] != "g.us"
	], ret);

def parseMsgSecurity(msg):
	if len(msg) != 3 or msg[0] != "security":
		raise ValueError("invalid security message");
	attrs = getAttrs(msg);
	timestamp = int(getAttr(attrs, "t")) if hasAttr(attrs, "t") else 0;
	id = getAttr(attrs, "id");
	jid = getAttr(attrs, "jid");
	isOwner = getAttr(attrs, "owner") == "true";
	participant = getAttr(attrs, "participant");
	type = getAttr(attrs, "type");
	typeAttr = None;

	if type == "identity":
		participantChild = findTagInArray(msg[2], "participant");
		if participantChild is not None:
			typeAttr = getAttr(participantChild[1], "jid");
	elif type == "encrypt":
		pass;
	
	msgKey = createWebMessageInfoMsgKey({
		"fromMe": isOwner,
		"remote": jid,
		"id": id,
		"participant": participant
	});
	ret = {
		"id": msgKey,
		"t": timestamp,
		"participant": participant,
		"type": "e2e_notification",
		"subtype": type,
		"from": connInfo["me"] if isOwner else jid,
		"to": jid if isOwner else connInfo["me"],
		"body": typeAttr
	};
	return dropIfConditionMet([
		not bool(id), not bool(timestamp), not bool(jid),
		type not in ["identity", "encrypt"],
		type == "identity" and not bool(typeAttr)
	], ret);

def parseMsg(msg, tag):
	if len(msg) != 3:
		raise ValueError("invalid msg");

	if msg[0] == "message":
		return parseMsgMessage(msg, tag);
	elif msg[0] == "groups_v2":
		return parseMsgGp2(msg);
	elif msg[0] == "broadcast":
		return parseMsgBroadcast(msg);
	elif msg[0] == "notification":
		return parseMsgNotification(msg);
	elif msg[0] == "call_log":
		return parseMsgCallLog(msg);
	elif msg[0] == "security":
		return parseMsgSecurity(msg);

def parseMsgList(msgs, tag):
	ret = [];
	for currMsg in msgs:
		parsedMsg = parseMsg(currMsg, tag);
		if parsedMsg is not None:
			ret.append(parsedMsg);
	return ret;

def msgGetTarget(msg):
	return getAttr(msg, "to") if getAttr(msg, "from") == connInfo["me"] else getAttr(msg, "from");

def handleActionMsg(actionMeta, actionGroup, node):
	addParam = getAttr(actionMeta, "add");
	if addParam == "relay" or addParam == "update":
		if len(actionGroup) != 1:
			raise ValueError("msg relay length is not 1");
		parsedMessage = parseMsg(actionGroup[0], "relay");
		if parsedMessage is None:
			raise ValueError("msg relay dropped: " + json.dumps(actionGroup[0]));
		messageTarget = msgGetTarget(parsedMessage);
		return [{						# app2***:695: Store.Msg.handle called with this array
			"meta": actionMeta,
			"chat": messageTarget,
			"msg": parsedMessage
		}];

	elif addParam == "last":
		parsedMessages = parseMsgList(actionGroup, "last");
		if len(parsedMessages) == 0:
			raise ValueError("msg last dropped to 0");
		messagesToHandle = { "recent": True, "meta": actionMeta };
		for currMessage in parsedMessages:
			messagesToHandle[msgGetTarget(currMessage)] = currMessage;
		return [messagesToHandle];		# app2***:715: Store.Msg.handle called with this array

	elif addParam == "before" or addParam == "after" or addParam == "unread":
		if len(actionGroup) == 0:
			raise ValueError("handle action msg " + addParam + " before/after 0 msgs");
		parsedMessages = parseMsgList(actionGroup, addParam);
		if len(parsedMessages) == 0:
			raise ValueError("handle action msg " + addParam + " dropped to 0");
		messageTarget = msgGetTarget(parsedMessages[0]);
		return [{						# app2***:730: Store.Msg.handle called with this array
			"meta": actionMeta,
			"chat": messageTarget,
			"msgs": parsedMessages
		}];
	
	elif addParam is not None:
		raise ValueError("invalid action msg 'add' attr: " + addParam);

def parseCmd(action):			# continue at app2***:6413
	if len(action) != 3:
		return;
	if getTag(action) == "read":
		attrs = getAttrs(action);
		jid = getAttr(attrs, "jid");
		isUnread = getAttr(attrs, "type") == "false";
		isStatus = getAttr(attrs, "kind") == "status";
		checksum = getAttr(attrs, "checksum");
		index = getAttr(attrs, "index");
		fromMe = getAttr(attrs, "owner") == "true";
		participant = getAttr(attrs, "participant");
		chat = getAttr(attrs, "chat");
		key = {				# TODO: wrap in try/except; also this is probably incomplete --> which function wraps this object? (app2***:6418)
			"id": index,
			"fromMe": fromMe,
			"remote": jid,
			"participant": participant
		};
		ret = {
			"type": "unread" if isUnread else "read",
			"jid": jid,
			"isStatus": isStatus,
			"checksum": checksum,
			"chat": decodeJid(chat),
			"key": key
		};
		return dropIfConditionMet([
			not bool(jid),
			isStatus and not bool(key)
		], ret);

	elif getTag(action) == "identity":
		identity = parseIdentity(action);
		if bool(identity):
			identity["type"] = "identity";
			return identity;
	return;

def parseIdentity(action):
	if len(action) != 3 or getTag(action) != "identity":
		return;
	attrs = getAttrs(action);
	children = getChildren(action);
	rawNode = findTagInArray(children, "raw");
	textNode = findTagInArray(children, "text");
	if bool(raw) and bool(text) and isinstance(getChildren(rawNode), basestring):
		dataStr = getChildren(textNode);		# TODO: original code uses 'dataStr' function, which indicates a 'byteLength' property for children (app2***:33537 / app2***:5031)
		return {
			"jid": getAttr(attrs, "jid"),
			"binary": getChildren(rawNode),
			"string": dataStr
		};
	return;

def parseContact(action):
	if len(action) != 3 or getTag(action) != "user":
		return;
	attrs = getAttrs(action);
	jid = getAttr(attrs, "jid");
	name = getAttr(attrs, "name");
	short = getAttrOrElse(attrs, "short", None);
	type = getAttrOrElse(attrs, "type", "in");
	notify = getAttr(attrs, "notify");
	verify = getAttr(attrs, "verify");
	isStatusMute = getAttr(attrs, "status_mute") == "true";
	index = getAttrOrElse(attrs, "index", None);
	hasCheckmark = getAttr(attrs, "checkmark") != "false";
	vname = getAttr(attrs, "vname");

	verified = None;
	verifiedLevel = None;
	if verify == "true" or verify == "0" or verify == "1" or verify == "2":
		verified = True;
		verifiedLevel = safeParseInt(verify, 0);
	else:
		verified = False;
		hasCheckmark = None;
	
	ret = {
		"id": jid,
		"name": vname if name is None else name,
		"type": type,
		"shortName": short,
		"plaintextDisabled": True,
		"pushname": notify,
		"verified": verified,
		"verifiedLevel": verifiedLevel,
		"statusMute": isStatusMute,
		"sectionHeader": index,
		"verifiedName": vname
	};
	if isinstance(hasCheckmark, bool):
		ret["verifiedCheckmark"] = hasCheckmark;
	return dropIfConditionMet([
		not bool(jid), type not in ["in", "out"] and bool(type)
	], ret);

def parseContacts(action):
	if len(action) != 3 or action[0] != "contacts":
		return;
	ret = None;
	type = getAttr(action[1], "type");
	children = action[2];
	if type == "frequent" and isinstance(action[2], list):
		for contact in action[2]:
			if not isinstance(contact, list) or len(contact) != 3:
				continue;
			contactTag = contact[0];
			if contactTag == "image" or contactTag == "video" or contactTag == "message":
				contactJid = getAttr(contact[1], "jid");
				if contactJid is not None:
					if ret is None:
						ret = {"type": "frequent"};
					if not contactTag in ret:
						ret[contactTag] = [];
					ret[contactTag].append(contactJid);
	return ret;

def parseChat(action):
	if len(action) != 3 or action[0] != "chat":
		return;
	attrs = getAttrs(action);
	jid = getAttr(attrs, "jid");
	timestamp = getAttrInt(attrs, "t");
	type = getAttr(attrs, "type");
	kind = getAttr(attrs, "kind");
	muteExpiration = getAttrInt(attrs, "mute");
	before = getAttrInt(attrs, "before");
	isArchive = getAttr(attrs, "archive") == "true";
	isReadOnly = getAttr(attrs, "read_only") == "true";
	modifyTag = getAttrInt(attrs, "modify_tag");
	name = getAttrOrElse(attrs, "name", None);
	unreadCount = getAttrInt(attrs, "count");
	pendingMsgs = getAttr(attrs, "message") == "true";
	hasStar = getAttr(attrs, "star") == "true";
	notSpam = getAttr(attrs, "spam") == "false";
	pin = getAttrInt(attrs, "pin", 0);

	if kind in ["text", "image", "video", "gif", "audio", "ptt", "document", "location", "vcard", "url"]:
		pass;
	else:
		kind = None;
	if type == "ahead":
		type = "clear";
	
	children = getChildren(action);
	items = None;
	if isinstance(children, list):
		items = [];
		for item in children:
			if getTag(item) == "item":
				itemAttrs = getAttrs(item);
				index = getAttr(itemAttrs, "index");
				if bool(index):
					items.push([index, getAttr(itemAttrs, "owner") == "true", getAttr(itemAttrs, "participant")]);
			else:
				msgMessage = parseMsgMessage(item, "response");
				if bool(msgMessage):
					items.push(msgMessage);
	ret = filterNone({
		"id": jid,
		"t": timestamp,
		"type": type,
		"kind": kind,
		"keys": items,
		"before": before,
		"archive": isArchive,
		"isReadOnly": isReadOnly,
		"unreadCount": unreadCount,
		"muteExpiration": muteExpiration,
		"modifyTag": modifyTag,
		"name": name,
		"pendingMsgs": pendingMsgs,
		"star": hasStar,
		"notSpam": notSpam,
		"pin": pin
	});
	return dropIfConditionMet([
		bool(type) and type not in ["delete", "clear", "archive", "unarchive", "mute", "star", "unstar", "spam", "modify_tag", "pin"],
		not bool(type) and not bool(jid),
		isArchive and bool(type) and type != "clear",
		type != "clear" and bool(before) and before > 0,
		type not in ["clear", "star", "unstar"] and bool(items) and len(items) > 0
	], ret);

def parseBattery(action):
	if len(action) != 3 or action[0] != "battery":
		return;
	ret = {};
	attrs = action[1];
	batteryValue = getAttr(attrs, "value");
	plugged = getAttr(attrs, "live");
	ret["battery"] = min(-1 if batteryValue is None else int(batteryValue), 100);
	if ret["battery"] == -1:
		return;
	if plugged is not None:
		ret["plugged"] = plugged;
	return ret;





def handleResponse(node, nodeName):			# defined at app2***:648
	if nodeName.find("preempt") == -1:
		raise ValueError("handle non-preemptive response: " + nodeName);
	attrs = getAttrs(node);
	type = getAttr(attrs, "type");
	if type == "chat":
		children = getChildren(node);
		allChats = [];
		if isinstance(children, list):
			for chat in children:
				currChat = parseChat(chat);
				if currChat is not None:
					allChats.append(currChat);
		return [{							# app2***:658: Store.Chat.handle called with this array
			"cmd": "preempt",
			"response": allChats
		}];
	elif type == "contacts":
		children = getChildren(node);
		allContacts = [];
		if isinstance(children, list):
			for contact in children:
				currContact = parseContact(contact);
				if currContact is not None:
					allContacts.append(currContact);
		return [{
			"cmd": "preempt",
			"checksum": getAttr(attrs, "checksum"),
			"response": allContacts
		}];
	else:
		raise ValueError("handle unknown response type: " + type);

def handleAction(node, nodeName):			# defined at app2***:745    actionsGetMeta at app2***:80
	actionMeta = actionGetMeta(node);
	groupedActions = groupActionsByType(node[2]);
	actionKeys = list(groupedActions.keys());

	if len(actionKeys) == 0 and getAttr(actionMeta, "add") == "last":
		print "WARNING in handleAction: ignored special case";
		return;		# TODO!

	for currActionKey in actionKeys:
		currActionGroup = groupedActions[currActionKey];
		if currActionKey == "msg":
			return { "meta": actionMeta, "actionKey": currActionKey, "node": handleActionMsg(actionMeta, currActionGroup, node) };
		elif currActionKey == "cmd":						# defined at app2***:761
			parsedCmds = [];
			for currCmd in currActionGroup:
				parsedCmds.append([parseCmd(currCmd)]);		# in original code: Store.Cmd.handle(...);
			return parsedCmds;
		elif currActionKey == "bcUpdate":
			print "WARNING in handleAction: ignored " + currActionKey;
			pass;
		elif currActionKey == "ack":
			print "WARNING in handleAction: ignored " + currActionKey;
			pass;
		elif currActionKey == "contact":
			print "WARNING in handleAction: ignored " + currActionKey;
			pass;
		elif currActionKey == "contacts":
			return [parseContacts(currActionGroup[0])];		# in original code: Store.Contact.handle(...)
		elif currActionKey == "chat":
			print "WARNING in handleAction: ignored " + currActionKey;
			pass;
		elif currActionKey == "battery":
			return [parseBattery(currActionGroup[0])];		# in original code: Store.Conn.handle(...)
		elif currActionKey == "mute":
			print "WARNING in handleAction: ignored " + currActionKey;
			pass;
		elif currActionKey == "status":
			print "WARNING in handleAction: ignored " + currActionKey;
			pass;
		elif currActionKey == "location":
			print "WARNING in handleAction: ignored " + currActionKey;
			pass;
		else:
			raise ValueError("invalid action key: " + currActionKey);





def handle(node, nodeName):
	#print json.dumps(node, indent=4, ensure_ascii=False);
	if len(node) != 3:
		raise ValueError("invalid node");

	tag = node[0];
	if tag == "response":
		return handleResponse(node, nodeName);
	elif tag == "action":
		return handleAction(node, nodeName);
	elif tag == "read":
		print "WARNING in handle: ignored " + tag;
		pass;
	else:
		raise ValueError("unknown node tag: " + tag);



def processData(nodeName, data, doFilterNone=True, me=connInfo["me"], debug=False):
	connInfo["me"] = me;
	msg = MessageParser(data);
	msgNode = msg.readNode();
	if debug:
		print json.dumps(msgNode, indent=4, ensure_ascii=False);
	handledMsg = handle(msgNode, nodeName);
	return filterNone(handledMsg) if doFilterNone else handledMsg;

'''
if len(sys.argv) == 1:
	print "usage: " + sys.argv[0] + " [file]";
	exit();
with open(sys.argv[1], "rb") as f:
	msg = MessageParser(f.read())

nodeName = sys.argv[1].split("_", 1)[1];
print json.dumps(filterNone(handle(msg.readNode(), nodeName)), indent=4, sort_keys=True);
'''
