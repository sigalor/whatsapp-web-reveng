from google.protobuf import json_format;
import json;
import whatsapp_protobuf_pb2;



class WATags:
	LIST_EMPTY      = 0;
	STREAM_END      = 2;
	DICTIONARY_0    = 236;
	DICTIONARY_1    = 237;
	DICTIONARY_2    = 238;
	DICTIONARY_3    = 239;
	LIST_8          = 248;
	LIST_16         = 249;
	JID_PAIR        = 250;
	HEX_8           = 251;
	BINARY_8        = 252;
	BINARY_20       = 253;
	BINARY_32       = 254;
	NIBBLE_8        = 255;
	SINGLE_BYTE_MAX = 256;
	PACKED_MAX      = 254;

	@staticmethod
	def get(str):
		return WATags.__dict__[str];



WASingleByteTokens = [
	None,None,None,"200","400","404","500","501","502","action","add",
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
	"unsubscribe","disable","vname","old_jid","new_jid","announcement",
	"locked","prop","label","color","call","offer","call-id"
];

WADoubleByteTokens = [];



class WAMetrics:
	DEBUG_LOG            = 1;
	QUERY_RESUME         = 2;
	QUERY_RECEIPT        = 3;
	QUERY_MEDIA          = 4;
	QUERY_CHAT           = 5;
	QUERY_CONTACTS       = 6;
	QUERY_MESSAGES       = 7;
	PRESENCE             = 8;
	PRESENCE_SUBSCRIBE   = 9;
	GROUP                = 10;
	READ                 = 11;
	CHAT                 = 12;
	RECEIVED             = 13;
	PIC                  = 14;
	STATUS               = 15;
	MESSAGE              = 16;
	QUERY_ACTIONS        = 17;
	BLOCK                = 18;
	QUERY_GROUP          = 19;
	QUERY_PREVIEW        = 20;
	QUERY_EMOJI          = 21;
	QUERY_MESSAGE_INFO   = 22;
	SPAM                 = 23;
	QUERY_SEARCH         = 24;
	QUERY_IDENTITY       = 25;
	QUERY_URL            = 26;
	PROFILE              = 27;
	CONTACT              = 28;
	QUERY_VCARD          = 29;
	QUERY_STATUS         = 30;
	QUERY_STATUS_UPDATE  = 31;
	PRIVACY_STATUS       = 32;
	QUERY_LIVE_LOCATIONS = 33;
	LIVE_LOCATION        = 34;
	QUERY_VNAME          = 35;
	QUERY_LABELS         = 36;
	CALL                 = 37;
	QUERY_CALL           = 38;
	QUERY_QUICK_REPLIES  = 39;

	@staticmethod
	def get(str):
		return WAMetrics.__dict__[str];



class WAFlags:
	IGNORE        = 1 << 7;
	ACK_REQUEST   = 1 << 6;
	AVAILABLE     = 1 << 5;
	NOT_AVAILABLE = 1 << 4;
	EXPIRES       = 1 << 3;
	SKIP_OFFLINE  = 1 << 2;

	@staticmethod
	def get(str):
		return WAFlags.__dict__[str];



class WAMediaAppInfo:
	imageMessage    = "WhatsApp Image Keys";
	videoMessage    = "WhatsApp Video Keys";
	audioMessage    = "WhatsApp Audio Keys";
	documentMessage = "WhatsApp Document Keys";

	@staticmethod
	def get(str):
		return WAMediaAppInfo.__dict__[str];



class WAWebMessageInfo:
	@staticmethod
	def decode(data):
		msg = whatsapp_protobuf_pb2.WebMessageInfo();
		msg.ParseFromString(data);
		return json.loads(json_format.MessageToJson(msg));
	
	@staticmethod
	def encode(msg):
		data = json_format.Parse(json.dumps(msg), whatsapp_protobuf_pb2.WebMessageInfo(), ignore_unknown_fields=True);
		return data.SerializeToString();
