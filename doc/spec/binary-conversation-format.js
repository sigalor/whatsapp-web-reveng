/**
 * Specification of all possible message types regarding the binary
 * conversation format. They are semantically grouped into four classes and
 * one class for meta information. Please refer to the comments besides the
 * types for specific information on them.
 * 
 * Information:
 *  - "VARINT" and "VARINT_ALT" are treated completely the same, maybe one of
 *    them still exists for backward compatibility.
 *  - All multi-byte types are in big endian.
 * 
 * Issues:
 *  - The purposes of "BASE_TYPE_MASK", "FORCE_VARINT_DATA" and "BIT8_SET"
 *    are not yet known, but not used anywhere else either.
*/
const WAMsgTypes = {
	//type class 0 (varint related)
	VARINT_INT32          : 1,			//reads varint, only interval [-(1<<31); 1<<31[ is valid
	VARINT                : 2,
	VARINT_UINT32         : 3,			//reads varint, only interval [0, 1<<32[ is valid
	VARINT_POSITIVE       : 4,			//reads varint, only interval [0, Infinity] is valid
	VARINT_SIGNED_INT32   : 5,			//first reads varint_uint32, then sign bit is the lowest bit
	VARINT_SIGNED         : 6,			//first reads varint, then sign bit is the lowest bit
	BOOLEAN               : 7,			//reads varint, only interval [0, 1] is valid
	VARINT_ALT            : 8,

	//type class 1 (64 bit)
	UINT64                : 9,
	INT64                 : 10,
	FLOAT64               : 11,

	//type class 2 (varint length + data)
	STRING                : 12,			//with byte length as VARINT before the string's UTF-8 bytes
	BYTES                 : 13,			//with length as VARINT before the bytes
	SUBMESSAGE            : 14,

	//type class 5 (32 bit)
	UINT32                : 15,
	INT32                 : 16,
	FLOAT32               : 17,

	//type class modifiers
	BASE_TYPE_MASK        : 31,
	IS_ARRAY              : 64,
	FORCE_VARINT_DATA     : 128,
	BIT8_SET              : 256
};

/**
 * Respecification for the four actual type classes.
 * "TYPE_CLASS_BITWIDTH" exists to know how many bits a type class value
 * needs. As these values are always below eight, only three bits are used.
 * "TYPE_CLASS_MASK" is just "(1<<TYPE_CLASS_BITWIDTH)-1" to provide a
 * reliable bitmask for a type class value.
 */
const WAMsgTypeClasses = {
	VARINT              : 0,
	BITS_64             : 1,
	VARINT_DATA         : 2,
	BITS_32             : 5,

	TYPE_CLASS_BITWIDTH : 3,
	TYPE_CLASS_MASK     : 7
};



/**
 * Specification of various meta information used in the binary conversation
 * format. This is not strictly necessary, but provides a useful reference for
 * how to interpret some values.
 */
const WAMetaInfo = {
	FONTTYPE: {
		SANS_SERIF: 0,
		SERIF: 1,
		NORICAN_REGULAR: 2,
		BRYNDAN_WRITE: 3,
		BEBASNEUE_REGULAR: 4,
		OSWALD_HEAVY: 5
	},
	ATTRIBUTION: {
		NONE: 0,
		GIPHY: 1,
		TENOR: 2
	},
	TYPE: {
		REVOKE: 0
	},
	DAYOFWEEKTYPE: {
		MONDAY: 1,
		TUESDAY: 2,
		WEDNESDAY: 3,
		THURSDAY: 4,
		FRIDAY: 5,
		SATURDAY: 6,
		SUNDAY: 7
	},
	CALENDARTYPE: {
		GREGORIAN: 1,
		SOLAR_HIJRI: 2
	}
};



/**
 * Specification for the actual message definitions.
 * 
 * To read a submessage, exactly three parts of information are needed:
 * its name, a field value and the type specification. This type consists of
 * a base type which may be modified using another bit. Currently, the only
 * modification is "IS_ARRAY".
 * 
 * Information:
 *  - When starting to read a binary conversation, the "__messageFrame"
 *    definition is used initially.
 *  - Generally, when "WAMsgTypes.SUBMESSAGE" is encountered, the decoder
 *    routine shall recursively reads a submessage with the name of the current
 *    property. This name is different if the "subMsgRef" attribute is set.
 *    A name change is mostly necessary when "WAMsgTypes.IS_ARRAY" is used
 *    and the name of a child is singular. The "WAMessageDefs" object always
 *    has to have an attribute with the current name.
 *  - If the "objRef" attribute is set, the current submessage generally
 *    consists of an integer type and references a value in the "WAMetaInfo"
 *    object.
 */
const WAMessageDefs = {
	"__messageFrame": [
		{ name: "key",                                        field: 1,  type: WAMsgTypes.BIT8_SET | WAMsgTypes.SUBMESSAGE },
		{ name: "message",                                    field: 2,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "messageTimestamp",                           field: 3,  type: WAMsgTypes.VARINT_POSITIVE },
		{ name: "status",                                     field: 4,  type: WAMsgTypes.VARINT },
		{ name: "participant",                                field: 5,  type: WAMsgTypes.STRING },
		{ name: "ignore",                                     field: 16, type: WAMsgTypes.BOOLEAN },
		{ name: "starred",                                    field: 17, type: WAMsgTypes.BOOLEAN },
		{ name: "broadcast",                                  field: 18, type: WAMsgTypes.BOOLEAN },
		{ name: "pushName",                                   field: 19, type: WAMsgTypes.STRING },
		{ name: "mediaCiphertextSha256",                      field: 20, type: WAMsgTypes.BYTES },
		{ name: "multicast",                                  field: 21, type: WAMsgTypes.BOOLEAN },
		{ name: "urlText",                                    field: 22, type: WAMsgTypes.BOOLEAN },
		{ name: "urlNumber",                                  field: 23, type: WAMsgTypes.BOOLEAN },
		{ name: "messageStubType",                            field: 24, type: WAMsgTypes.VARINT },
		{ name: "clearMedia",                                 field: 25, type: WAMsgTypes.BOOLEAN },
		{ name: "messageStubParameters",                      field: 26, type: WAMsgTypes.IS_ARRAY | WAMsgTypes.STRING },
		{ name: "duration",                                   field: 27, type: WAMsgTypes.VARINT_UINT32 }
	],
	"key": [
		{ name: "remoteJid",                                  field: 1,  type: WAMsgTypes.STRING },
		{ name: "fromMe",                                     field: 2,  type: WAMsgTypes.BOOLEAN },
		{ name: "id",                                         field: 3,  type: WAMsgTypes.STRING },
		{ name: "participant",                                field: 4,  type: WAMsgTypes.STRING }
	],
	"message": [
		{ name: "conversation",                               field: 1,  type: WAMsgTypes.STRING },
		{ name: "senderKeyDistributionMessage",               field: 2,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "imageMessage",                               field: 3,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "contactMessage",                             field: 4,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "locationMessage",                            field: 5,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "extendedTextMessage",                        field: 6,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "documentMessage",                            field: 7,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "audioMessage",                               field: 8,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "videoMessage",                               field: 9,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "call",                                       field: 10, type: WAMsgTypes.SUBMESSAGE },
		{ name: "chat",                                       field: 11, type: WAMsgTypes.SUBMESSAGE },
		{ name: "protocolMessage",                            field: 12, type: WAMsgTypes.SUBMESSAGE },
		{ name: "contactsArrayMessage",                       field: 13, type: WAMsgTypes.SUBMESSAGE },
		{ name: "highlyStructuredMessage",                    field: 14, type: WAMsgTypes.SUBMESSAGE },
		{ name: "fastRatchetKeySenderKeyDistributionMessage", field: 15, type: WAMsgTypes.SUBMESSAGE, subMsgRef: "senderKeyDistributionMessage" },
		{ name: "sendPaymentMessage",                         field: 16, type: WAMsgTypes.SUBMESSAGE },
		{ name: "requestPaymentMessage",                      field: 17, type: WAMsgTypes.SUBMESSAGE },
		{ name: "liveLocationMessage",                        field: 18, type: WAMsgTypes.SUBMESSAGE },
		{ name: "stickerMessage",                             field: 19, type: WAMsgTypes.SUBMESSAGE }
	],



	"senderKeyDistributionMessage": [
		{ name: "groupId",                                    field: 1,  type: WAMsgTypes.STRING },
		{ name: "axolotlSenderKeyDistributionMessage",        field: 2,  type: WAMsgTypes.BYTES },
	],
	"imageMessage": [	
		{ name: "url",                                        field: 1,  type: WAMsgTypes.STRING },
		{ name: "mimetype",                                   field: 2,  type: WAMsgTypes.STRING },
		{ name: "caption",                                    field: 3,  type: WAMsgTypes.STRING },
		{ name: "fileSha256",                                 field: 4,  type: WAMsgTypes.BYTES },
		{ name: "fileLength",                                 field: 5,  type: WAMsgTypes.VARINT_POSITIVE },
		{ name: "height",                                     field: 6,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "width",                                      field: 7,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "mediaKey",                                   field: 8,  type: WAMsgTypes.BYTES },
		{ name: "fileEncSha256",                              field: 9,  type: WAMsgTypes.BYTES },
		{ name: "interactiveAnnotations",                     field: 10, type: WAMsgTypes.IS_ARRAY | WAMsgTypes.SUBMESSAGE, subMsgRef: "interactiveAnnotation" },
		{ name: "directPath",                                 field: 11, type: WAMsgTypes.STRING },
		{ name: "jpegThumbnail",                              field: 16, type: WAMsgTypes.BYTES },
		{ name: "contextInfo",                                field: 17, type: WAMsgTypes.SUBMESSAGE },
		{ name: "firstScanSidecar",                           field: 18, type: WAMsgTypes.BYTES },
		{ name: "firstScanLength",                            field: 19, type: WAMsgTypes.VARINT_UINT32 }
	],
	"contactMessage": [
		{ name: "displayName",                                field: 1,  type: WAMsgTypes.STRING },
		{ name: "vcard",                                      field: 16, type: WAMsgTypes.STRING },
		{ name: "contextInfo",                                field: 17, type: WAMsgTypes.SUBMESSAGE }
	],
	"locationMessage": [
		{ name: "degreesLatitude",                            field: 1,  type: WAMsgTypes.FLOAT64 },
		{ name: "degreesLongitude",                           field: 2,  type: WAMsgTypes.FLOAT64 },
		{ name: "name",                                       field: 3,  type: WAMsgTypes.STRING },
		{ name: "address",                                    field: 4,  type: WAMsgTypes.STRING },
		{ name: "url",                                        field: 5,  type: WAMsgTypes.STRING },
		{ name: "jpegThumbnail",                              field: 16, type: WAMsgTypes.BYTES },
		{ name: "contextInfo",                                field: 17, type: WAMsgTypes.SUBMESSAGE }
	],
	"extendedTextMessage": [
		{ name: "text",                                       field: 1,  type: WAMsgTypes.STRING },
		{ name: "matchedText",                                field: 2,  type: WAMsgTypes.STRING },
		{ name: "canonicalUrl",                               field: 4,  type: WAMsgTypes.STRING },
		{ name: "description",                                field: 5,  type: WAMsgTypes.STRING },
		{ name: "title",                                      field: 6,  type: WAMsgTypes.STRING },
		{ name: "textArgb",                                   field: 7,  type: WAMsgTypes.UINT32 },
		{ name: "backgroundArgb",                             field: 8,  type: WAMsgTypes.UINT32 },
		{ name: "font",                                       field: 9,  type: WAMsgTypes.VARINT, objRef: WAMetaInfo.FONTTYPE },
		{ name: "jpegThumbnail",                              field: 16, type: WAMsgTypes.BYTES },
		{ name: "contextInfo",                                field: 17, type: WAMsgTypes.SUBMESSAGE }
	],
	"documentMessage": [
		{ name: "url",                                        field: 1,  type: WAMsgTypes.STRING },
		{ name: "mimetype",                                   field: 2,  type: WAMsgTypes.STRING },
		{ name: "title",                                      field: 3,  type: WAMsgTypes.STRING },
		{ name: "fileSha256",                                 field: 4,  type: WAMsgTypes.BYTES },
		{ name: "fileLength",                                 field: 5,  type: WAMsgTypes.VARINT_POSITIVE },
		{ name: "pageCount",                                  field: 6,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "mediaKey",                                   field: 7,  type: WAMsgTypes.BYTES },
		{ name: "fileName",                                   field: 8,  type: WAMsgTypes.STRING },
		{ name: "fileEncSha256",                              field: 9,  type: WAMsgTypes.BYTES },
		{ name: "directPath",                                 field: 10, type: WAMsgTypes.STRING },
		{ name: "jpegThumbnail",                              field: 16, type: WAMsgTypes.BYTES },
		{ name: "contextInfo",                                field: 17, type: WAMsgTypes.SUBMESSAGE }
	],
	"audioMessage": [
		{ name: "url",                                        field: 1,  type: WAMsgTypes.STRING },
		{ name: "mimetype",                                   field: 2,  type: WAMsgTypes.STRING },
		{ name: "fileSha256",                                 field: 3,  type: WAMsgTypes.BYTES },
		{ name: "fileLength",                                 field: 4,  type: WAMsgTypes.VARINT_POSITIVE },
		{ name: "seconds",                                    field: 5,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "ptt",                                        field: 6,  type: WAMsgTypes.BOOLEAN },
		{ name: "mediaKey",                                   field: 7,  type: WAMsgTypes.BYTES },
		{ name: "fileEncSha256",                              field: 8,  type: WAMsgTypes.BYTES },
		{ name: "directPath",                                 field: 9,  type: WAMsgTypes.STRING },
		{ name: "contextInfo",                                field: 17, type: WAMsgTypes.SUBMESSAGE },
		{ name: "streamingSidecar",                           field: 18, type: WAMsgTypes.BYTES }
	],
	"videoMessage": [
		{ name: "url",                                        field: 1,  type: WAMsgTypes.STRING },
		{ name: "mimetype",                                   field: 2,  type: WAMsgTypes.STRING },
		{ name: "fileSha256",                                 field: 3,  type: WAMsgTypes.BYTES },
		{ name: "fileLength",                                 field: 4,  type: WAMsgTypes.VARINT_POSITIVE },
		{ name: "seconds",                                    field: 5,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "mediaKey",                                   field: 6,  type: WAMsgTypes.BYTES },
		{ name: "caption",                                    field: 7,  type: WAMsgTypes.STRING },
		{ name: "gifPlayback",                                field: 8,  type: WAMsgTypes.BOOLEAN },
		{ name: "height",                                     field: 9,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "width",                                      field: 10, type: WAMsgTypes.VARINT_UINT32 },
		{ name: "fileEncSha256",                              field: 11, type: WAMsgTypes.BYTES },
		{ name: "interactiveAnnotations",                     field: 12, type: WAMsgTypes.IS_ARRAY | WAMsgTypes.SUBMESSAGE, subMsgRef: "interactiveAnnotation" },
		{ name: "directPath",                                 field: 13, type: WAMsgTypes.STRING },
		{ name: "jpegThumbnail",                              field: 16, type: WAMsgTypes.BYTES },
		{ name: "contextInfo",                                field: 17, type: WAMsgTypes.SUBMESSAGE },
		{ name: "streamingSidecar",                           field: 18, type: WAMsgTypes.BYTES },
		{ name: "gifAttribution",                             field: 19, type: WAMsgTypes.VARINT }
	],
	"call": [
		{ name: "callKey",                                    field: 1,  type: WAMsgTypes.BYTES }
	],
	"chat": [
		{ name: "displayName",                                field: 1,  type: WAMsgTypes.STRING },
		{ name: "id",                                         field: 2,  type: WAMsgTypes.STRING }
	],
	"protocolMessage": [
		{ name: "key",                                        field: 1,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "type",                                       field: 2,  type: WAMsgTypes.VARINT_ALT, objRef: WAMetaInfo.TYPE }
	],
	"contactsArrayMessage": [
		{ name: "displayName",                                field: 1,  type: WAMsgTypes.STRING },
		{ name: "contacts",                                   field: 2,  type: WAMsgTypes.IS_ARRAY | WAMsgTypes.SUBMESSAGE, subMsgRef: "contact" },
		{ name: "contextInfo",                                field: 17, type: WAMsgTypes.SUBMESSAGE },
	],
	"highlyStructuredMessage": [
		{ name: "namespace",                                  field: 1,  type: WAMsgTypes.STRING },
		{ name: "elementName",                                field: 2,  type: WAMsgTypes.STRING },
		{ name: "params",                                     field: 3,  type: WAMsgTypes.IS_ARRAY | WAMsgTypes.STRING },
		{ name: "fallbackLg",                                 field: 4,  type: WAMsgTypes.STRING },
		{ name: "fallbackLc",                                 field: 5,  type: WAMsgTypes.STRING },
		{ name: "localizableParams",                          field: 6,  type: WAMsgTypes.IS_ARRAY | WAMsgTypes.SUBMESSAGE, subMsgRef: "localizableParameter" }
	],
	"sendPaymentMessage": [
		{ name: "noteMessage",                                field: 2,  type: WAMsgTypes.SUBMESSAGE, subMsgRef: "message" }
	],
	"requestPaymentMessage": [
		{ name: "currencyCodeIso4217",                        field: 1,  type: WAMsgTypes.STRING },
		{ name: "amount1000",                                 field: 2,  type: WAMsgTypes.VARINT_POSITIVE },
		{ name: "requestFrom",                                field: 3,  type: WAMsgTypes.STRING },
		{ name: "noteMessage",                                field: 4,  type: WAMsgTypes.SUBMESSAGE, subMsgRef: "message" }
	],
	"liveLocationMessage": [
		{ name: "degreesLatitude",                            field: 1,  type: WAMsgTypes.FLOAT64 },
		{ name: "degreesLongitude",                           field: 2,  type: WAMsgTypes.FLOAT64 },
		{ name: "accuracyInMeters",                           field: 3,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "speedInMps",                                 field: 4,  type: WAMsgTypes.FLOAT32 },
		{ name: "degreesClockwiseFromMagneticNorth",          field: 5,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "caption",                                    field: 6,  type: WAMsgTypes.STRING },
		{ name: "sequenceNumber",                             field: 7,  type: WAMsgTypes.VARINT },
		{ name: "jpegThumbnail",                              field: 16, type: WAMsgTypes.BYTES },
		{ name: "contextInfo",                                field: 17, type: WAMsgTypes.SUBMESSAGE }
	],
	"stickerMessage": [
		{ name: "url",                                        field: 1,  type: WAMsgTypes.STRING },
		{ name: "fileSha256",                                 field: 2,  type: WAMsgTypes.BYTES },
		{ name: "fileEncSha256",                              field: 3,  type: WAMsgTypes.BYTES },
		{ name: "mediaKey",                                   field: 4,  type: WAMsgTypes.BYTES },
		{ name: "mimetype",                                   field: 5,  type: WAMsgTypes.STRING },
		{ name: "height",                                     field: 6,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "width",                                      field: 7,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "directPath",                                 field: 8,  type: WAMsgTypes.STRING },
		{ name: "fileLength",                                 field: 9,  type: WAMsgTypes.VARINT_POSITIVE },
		{ name: "pngThumbnail",                               field: 16, type: WAMsgTypes.BYTES },
		{ name: "contextInfo",                                field: 17, type: WAMsgTypes.SUBMESSAGE }
	],



	"interactiveAnnotation": [
		{ name: "polygonVertices",                            field: 1,  type: WAMsgTypes.IS_ARRAY | WAMsgTypes.SUBMESSAGE, subMsgRef: "point" },
		{ name: "location",                                   field: 2,  type: WAMsgTypes.SUBMESSAGE },
	],
	"point": [
		{ name: "x",                                          field: 3,  type: WAMsgTypes.FLOAT64 },
		{ name: "y",                                          field: 4,  type: WAMsgTypes.FLOAT64 }
	],
	"location": [
		{ name: "degreesLatitude",                            field: 1,  type: WAMsgTypes.FLOAT64 },
		{ name: "degreesLongitude",                           field: 2,  type: WAMsgTypes.FLOAT64 },
		{ name: "name",                                       field: 3,  type: WAMsgTypes.STRING }
	],



	"localizableParameter": [		//needs exactly "one of" the following two (not yet explicitly specified here)
		{ name: "currency",                                   field: 2,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "datetime",                                   field: 3,  type: WAMsgTypes.SUBMESSAGE },
	],
	"currency": [
		{ name: "currencyCode",                               field: 1,  type: WAMsgTypes.STRING },
		{ name: "amount1000",                                 field: 2,  type: WAMsgTypes.VARINT }
	],
	"datetime": [					//needs exactly "one of" the following two (not yet explicitly specified here)
		{ name: "component",                                  field: 1,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "unixEpoch",                                  field: 2,  type: WAMsgTypes.SUBMESSAGE },
	],
	"component": [
		{ name: "dayOfWeek",                                  field: 1,  type: WAMsgTypes.VARINT_ALT, objRef: WAMetaInfo.DAYOFWEEKTYPE },
		{ name: "year",                                       field: 2,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "month",                                      field: 3,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "dayOfMonth",                                 field: 4,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "hour",                                       field: 5,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "minute",                                     field: 6,  type: WAMsgTypes.VARINT_UINT32 },
		{ name: "calendar",                                   field: 7,  type: WAMsgTypes.VARINT_ALT, objRef: WAMetaInfo.CALENDARTYPE }
	],
	"unixEpoch": [
		{ name: "timestamp",                                  field: 1,  type: WAMsgTypes.VARINT }
	],



	"contextInfo": [
		{ name: "stanzaId",                                   field: 1,  type: WAMsgTypes.STRING },
		{ name: "participant",                                field: 2,  type: WAMsgTypes.STRING },
		{ name: "quotedMessage",                              field: 3,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "remoteJid",                                  field: 4,  type: WAMsgTypes.STRING },
		{ name: "mentionedJid",                               field: 15, type: WAMsgTypes.IS_ARRAY | WAMsgTypes.STRING },
		{ name: "conversionSource",                           field: 18, type: WAMsgTypes.STRING },
		{ name: "conversionData",                             field: 19, type: WAMsgTypes.BYTES },
		{ name: "conversionDelaySeconds",                     field: 20, type: WAMsgTypes.VARINT_UINT32 },
		{ name: "isForwarded",                                field: 22, type: WAMsgTypes.BOOLEAN },
	],
	"quotedMessage": [
		{ name: "conversation",                               field: 1,  type: WAMsgTypes.STRING },
		{ name: "senderKeyDistributionMessage",               field: 2,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "imageMessage",                               field: 3,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "contactMessage",                             field: 4,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "locationMessage",                            field: 5,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "extendedTextMessage",                        field: 6,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "documentMessage",                            field: 7,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "audioMessage",                               field: 8,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "videoMessage",                               field: 9,  type: WAMsgTypes.SUBMESSAGE },
		{ name: "call",                                       field: 10, type: WAMsgTypes.SUBMESSAGE },
		{ name: "chat",                                       field: 11, type: WAMsgTypes.SUBMESSAGE },
		{ name: "protocolMessage",                            field: 12, type: WAMsgTypes.SUBMESSAGE },
		{ name: "contactsArrayMessage",                       field: 13, type: WAMsgTypes.SUBMESSAGE },
		{ name: "highlyStructuredMessage",                    field: 14, type: WAMsgTypes.SUBMESSAGE },
		{ name: "fastRatchetKeySenderKeyDistributionMessage", field: 15, type: WAMsgTypes.SUBMESSAGE, subMsgRef: "senderKeyDistributionMessage" },
		{ name: "sendPaymentMessage",                         field: 16, type: WAMsgTypes.SUBMESSAGE },
		{ name: "requestPaymentMessage",                      field: 17, type: WAMsgTypes.SUBMESSAGE },
		{ name: "liveLocationMessage",                        field: 18, type: WAMsgTypes.SUBMESSAGE },
		{ name: "stickerMessage",                             field: 19, type: WAMsgTypes.SUBMESSAGE }
	]
};
