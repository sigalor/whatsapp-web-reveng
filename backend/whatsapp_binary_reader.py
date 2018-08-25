from whatsapp_defines import WATags, WASingleByteTokens, WADoubleByteTokens, WAWebMessageInfo;



class WABinaryReader:
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
		return self.readIntN(2, littleEndian);

	def readInt20(self):
		self.checkEOS(3);
		ret = ((ord(self.data[self.index]) & 15) << 16) + (ord(self.data[self.index+1]) << 8) + ord(self.data[self.index+2]);
		self.index += 3;
		return ret;

	def readInt32(self, littleEndian=False):
		return self.readIntN(4, littleEndian);

	def readInt64(self, littleEndian=False):
		return self.readIntN(8, littleEndian);

	def readPacked8(self, tag):
		startByte = self.readByte();
		ret = "";
		for i in range(startByte & 127):
			currByte = self.readByte();
			ret += self.unpackByte(tag, (currByte & 0xF0) >> 4) + self.unpackByte(tag, currByte & 0x0F);
		if (startByte >> 7) == 0:
			ret = ret[:len(ret)-1];
		return ret;

	def unpackByte(self, tag, value):
		if tag == WATags.NIBBLE_8:
			return self.unpackNibble(value);
		elif tag == WATags.HEX_8:
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

	def readRangedVarInt(self, minVal, maxVal, desc="unknown"):
		ret = self.readVarInt();
		if ret < minVal or ret >= maxVal:
			raise ValueError("varint for " + desc + " is out of bounds: " + str(ret));
		return ret;


	def isListTag(self, tag):
		return tag == WATags.LIST_EMPTY or tag == WATags.LIST_8 or tag == WATags.LIST_16;

	def readListSize(self, tag):
		if(tag == WATags.LIST_EMPTY):
			return 0;
		elif(tag == WATags.LIST_8):
			return self.readByte();
		elif(tag == WATags.LIST_16):
			return self.readInt16();
		raise ValueError("invalid tag for list size: " + str(tag));
	
	def readString(self, tag):
		if tag >= 3 and tag <= 235:
			token = self.getToken(tag);
			if token == "s.whatsapp.net":
				token = "c.us";
			return token;
		
		if tag == WATags.DICTIONARY_0 or tag == WATags.DICTIONARY_1 or tag == WATags.DICTIONARY_2 or tag == WATags.DICTIONARY_3:
			return self.getTokenDouble(tag - WATags.DICTIONARY_0, self.readByte());
		elif tag == WATags.LIST_EMPTY:
			return;
		elif tag == WATags.BINARY_8:
			return self.readStringFromChars(self.readByte());
		elif tag == WATags.BINARY_20:
			return self.readStringFromChars(self.readInt20());
		elif tag == WATags.BINARY_32:
			return self.readStringFromChars(self.readInt32());
		elif tag == WATags.JID_PAIR:
			i = self.readString(self.readByte());
			j = self.readString(self.readByte());
			if i is None or j is None:
				raise ValueError("invalid jid pair: " + str(i) + ", " + str(j));
			return i + "@" + j;
		elif tag == WATags.NIBBLE_8 or tag == WATags.HEX_8:
			return self.readPacked8(tag);
		else:
			raise ValueError("invalid string with tag " + str(tag));
	
	def readStringFromChars(self, length):
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
		listSize = self.readListSize(self.readByte());
		descrTag = self.readByte();
		if descrTag == WATags.STREAM_END:
			raise ValueError("unexpected stream end");
		descr = self.readString(descrTag);
		if listSize == 0 or not descr:
			raise ValueError("invalid node");
		attrs = self.readAttributes((listSize-1) >> 1);
		if listSize % 2 == 1:
			return [descr, attrs, None];

		tag = self.readByte();
		if self.isListTag(tag):
			content = self.readList(tag);
		elif tag == WATags.BINARY_8:
			content = self.readBytes(self.readByte());
		elif tag == WATags.BINARY_20:
			content = self.readBytes(self.readInt20());
		elif tag == WATags.BINARY_32:
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
		if index < 3 or index >= len(WASingleByteTokens):
			raise ValueError("invalid token index: " + str(index));
		return WASingleByteTokens[index];

	def getTokenDouble(self, index1, index2):
		n = 256 * index1 + index2;
		if n < 0 or n >= len(WADoubleByteTokens):
			raise ValueError("invalid token index: " + str(n));
		return WADoubleByteTokens[n];
		


def whatsappReadMessageArray(msgs):
	if not isinstance(msgs, list):
		return msgs;
	ret = [];
	for x in msgs:
		ret.append(WAWebMessageInfo.decode(x[2]) if isinstance(x, list) and x[0]=="message" else x);
	return ret;

def whatsappReadBinary(data, withMessages=False):
	node = WABinaryReader(data).readNode();
	if withMessages and node is not None and isinstance(node, list) and node[1] is not None:
		node[2] = whatsappReadMessageArray(node[2]);
	return node;
