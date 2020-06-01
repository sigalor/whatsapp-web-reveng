

# WhatsApp Web reverse engineered

## Introduction
This project intends to provide a complete description and re-implementation of the WhatsApp Web API, which will eventually lead to a custom client. WhatsApp Web internally works using WebSockets; this project does as well.

## Trying it out
Before you can run the application, make sure that you have the following software installed:

- Node.js (at least version 8, as the `async` `await` syntax is used)
- Python 2.7 with the following `pip` packages installed:
  - `websocket-client` and `git+https://github.com/dpallot/simple-websocket-server.git` for acting as WebSocket server and client.
  - `curve25519-donna` and `pycrypto` for the encryption stuff.
  - `pyqrcode` for QR code generation.
  - `protobuf` for reading and writing the binary conversation format.
- Note: On Windows `curve25519-donna` requires [Microsoft Visual C++ 9.0](http://aka.ms/vcpython27) and you need to copy [`stdint.h`](windows) into `C:\Users\YOUR USERNAME\AppData\Local\Programs\Common\Microsoft\Visual C++ for Python\9.0\VC\include`.

Before starting the application for the first time, run `npm install -f` to install all Node and `pip install -r requirements.txt` for all Python dependencies.

Lastly, to finally launch it, just run `npm start` on Linux based OS's and `npm run win` on Windows. Using fancy `concurrently` and `nodemon` magic, all three local components will be started after each other and when you edit a file, the changed module will automatically restart to apply the changes.

## Reimplementations

### JavaScript

A recent addition is a version of the decryption routine translated to in-browser JavaScript. Run `node index_jsdemo.js` (just needed because browsers don't allow changing HTTP headers for WebSockets), then open `client/login-via-js-demo.html` as a normal file in any browser. The console output should show decrypted binary messages after scanning the QR code.

[adiwajshing](https://github.com/adiwajshing) created [Baileys](https://github.com/adiwajshing/Baileys), a Node library that implements the WhatsApp Web API. 

[ndunks](https://github.com/ndunks) made a TypeScript reimplementation at [WaJs](https://github.com/ndunks/WaJs).

### Rust

With [whatsappweb-rs](https://github.com/wiomoc/whatsappweb-rs), [wiomoc](https://github.com/wiomoc) created a WhatsApp Web client in Rust.

### Go

[Rhymen](https://github.com/Rhymen) created [go-whatsapp](https://github.com/Rhymen/go-whatsapp), a Go package that implements the WhatsApp Web API.

### Clojure

[vzaramel](https://github.com/vzaramel) created [whatsappweb-clj](https://github.com/vzaramel/whatsappweb-clj), a Clojure library the implements the WhatsApp Web API.

## Application architecture
The project is organized in the following way. Note the used ports and make sure that they are not in use elsewhere before starting the application.
![whatsapp-web-reveng Application architecture](https://raw.githubusercontent.com/sigalor/whatsapp-web-reveng/master/doc/img/app-architecture1000.png)


## Login and encryption details
WhatsApp Web encrypts the data using several different algorithms. These include [AES 256 CBC](https://en.wikipedia.org/wiki/Advanced_Encryption_Standard), [Curve25519](https://en.wikipedia.org/wiki/Curve25519) as Diffie-Hellman key agreement scheme, [HKDF](https://en.wikipedia.org/wiki/HKDF) for generating the extended shared secret and [HMAC](https://en.wikipedia.org/wiki/Hash-based_message_authentication_code) with SHA256.

Starting the WhatsApp Web session happens by just connecting to one of its websocket servers at `wss://w[1-8].web.whatsapp.com/ws` (`wss://` means that the websocket connection is secure; `w[1-8]` means that any number between 1 and 8 can follow the `w`). Also make sure that, when establishing the connection, the HTTP header `Origin: https://web.whatsapp.com` is set, otherwise the connection will be rejected.

### Messages
When you send messages to a WhatsApp Web websocket, they need to be in a specific format. It is quite simple and looks like `messageTag,JSON`, e.g. `1515590796,["data",123]`. Note that apparently the message tag can be anything. This application mostly uses the current timestamp as tag, just to be a bit unique. WhatsApp itself often uses message tags like `s1`, `1234.--0` or something like that. Obviously the message tag may not contain a comma. Additionally, JSON _objects_ are possible as well as payload.

### Logging in
To log in at an open websocket, follow these steps:

1. Generate your own `clientId`, which needs to be 16 base64-encoded bytes (i.e. 25 characters). This application just uses 16 random bytes, i.e. `base64.b64encode(os.urandom(16))` in Python.
2. Decide for a tag for your message, which is more or less arbitrary (see above). This application uses the current timestamp (in seconds) for that. Remember this tag for later.
3. The message you send to the websocket looks like this: `messageTag,["admin","init",[0,3,2390],["Long browser description","ShortBrowserDesc"],"clientId",true]`.
	- Obviously, you need to replace `messageTag` and `clientId` by the values you chose before
	- The `[0,3,2390]` part specifies the current WhatsApp Web version. The last value changes frequently. It should be quite backwards-compatible though.
	- `"Long browser description"` is an arbitrary string that will be shown in the WhatsApp app in the list of registered WhatsApp Web clients after you scan the QR code.
	- `"ShortBrowserDesc"` has not been observed anywhere yet but is arbitrary as well.
4. After a few moments, your websocket will receive a message in the specified format with the message tag _you chose in step 2_. The JSON object of this message has the following attributes:
	- `status`: should be 200
	- `ref`: in the application, this is treated as the server ID; important for the QR generation, see below
	- `ttl`: is 20000, maybe the time after the QR code becomes invalid
	- `update`: a boolean flag
	- `curr`: the current WhatsApp Web version, e.g. `0.2.7314`
	- `time`: the timestamp the server responded at, as floating-point milliseconds, e.g. `1515592039037.0`

### QR code generation
5. Generate your own private key with Curve25519, e.g. `curve25519.Private()`.
6. Get the public key from your private key, e.g. `privateKey.get_public()`.
7. Obtain the string later encoded by the QR code by concatenating the following values with a comma:
	- the server ID, i.e. the `ref` attribute from step 4
	- the base64-encoded version of your public key, i.e. `base64.b64encode(publicKey.serialize())`
	- your client ID
8. Turn this string into an image (e.g. using `pyqrcode`) and scan it using the WhatsApp app.

### Requesting new ref for QR code generation (not implemented)
9. You can request up to 5 new server refs when previous one expires (`ttl`).
10. Do it by sending `messageTag,["admin","Conn","reref"]`.
11. The server responds with JSON with the following attributes:
	- `status`: should be 200 (other ones: 304 - reuse previous ref, 429 - new ref denied)
	- `ref`: new ref
	- `ttl`: expiration time
12. Update your QR code with the new ref.

### After scanning the QR code
13. Immediately after you scan the QR code, the websocket receives several important JSON messages that build up the encryption details. These use the specified message format and have a JSON _array_ as payload. Their message tag has no special meaning. The first entry of the JSON array has one of the following values:
	- `Conn`: array contains JSON object as second element with connection information containing the following attributes and many more:
		- `battery`: the current battery percentage of your phone
		- `browserToken`: used to logout without active WebSocket connection (not implemented yet)
		- `clientToken`: used to resuming closed sessions aka "Remember me" (not implemented yet)
		- `phone`: an object with detailed information about your phone, e.g. `device_manufacturer`, `device_model`, `os_build_number`, `os_version`
		- `platform`: your phone OS, e.g. `android`
		- `pushname`: the name of yours you provided WhatsApp
		- `secret` (remember this!)
		- `serverToken`: used to resuming closed sessions aka "Remember me" (not implemented yet)
		- `wid`: your phone number in the chat identification format (see below)
	- `Stream`: array has four elements in total, so the entire payload is like `["Stream","update",false,"0.2.7314"]`
	- `Props`: array contains JSON object as second element with several properties like `imageMaxKBytes` (1024), `maxParticipants` (257), `videoMaxEdge` (960) and others

### Key generation
14. You are now ready for generating the final encryption keys. Start by decoding the `secret` from `Conn` as base64 and storing it as `secret`. This decoded secret will be 144 bytes long.
15. Take the _first 32 bytes_ of the decoded secret and use it as a public key. Together with your private key, generate a shared key out of it and call it `sharedSecret`. The application does it using `privateKey.get_shared_key(curve25519.Public(secret[:32]), lambda a:a)`.
16. Extend `sharedSecret` to 80 bytes using HKDF. Call this value `sharedSecretExpanded`.
17. This step is optional, it validates the data provided by the server. The method is called _HMAC validation_. Do it by first calculating `HmacSha256(sharedSecretExpanded[32:64], secret[:32] + secret[64:])`. Compare this value to `secret[32:64]`. If they are not equal, abort the login.
18. You now have the encrypted keys: store `sharedSecretExpanded[64:] + secret[64:]` as `keysEncrypted`.
19. The encrypted keys now need to be decrypted using AES with `sharedSecretExpanded[:32]` as key, i.e. store `AESDecrypt(sharedSecretExpanded[:32], keysEncrypted)` as `keysDecrypted`.
20. The `keysDecrypted` variable is 64 bytes long and contains two keys, each 32 bytes long. The `encKey` is used for decrypting binary messages sent to you by the WhatsApp Web server or encrypting binary messages you send to the server. The `macKey` is needed to validate the messages sent to you:
	- `encKey`: `keysDecrypted[:32]`
	- `macKey`: `keysDecrypted[32:64]`
    
### Restoring closed sessions (not implemented)
1. After sending `init` command, check whether you have `serverToken` and `clientToken`.
2. If so, send `messageTag,["admin","login","clientToken","serverToken","clientId","takeover"]`
3. The server should respond with `{"status": 200}`. Other statuses:
	- 401: Unpaired from the phone
	- 403: Access denied, check `tos` field in the JSON: if it equals or greater than 2, you have violated TOS
	- 405: Already logged in
	- 409: Logged in from another location

### Resolving challenge (not implemented)
4. When using old or expired `serverToken` and `clientToken`, you will be challenged to confirm that you still have valid encryption keys.
5. The challenge looks like this `messageTag,["Cmd",{"type":"challenge","challenge":"BASE_64_ENCODED_STRING=="}]`
6. Decode `challenge` string from Base64, sign it with your macKey, encode it back with Base64 and send `messageTag,["admin","challenge","BASE_64_ENCODED_STRING==","serverToken","clientId"]`
7. The server should respond with `{"status": 200}`, but it means nothing.
8. After solving challenge your connection should be restored.

### Logging out
1. When you have an active WebSocket connection, just send `goodbye,,["admin","Conn","disconnect"]`.
2. When you don't have such connection (for example your session has been taken over from another location), sign your `encKey` with your `macKey` and encode it with Base64. Let's say it is your `logoutToken`.
3. Send a POST request to `https://dyn.web.whatsapp.com/logout?t=browserToken&m=logoutToken`
4. Remember to always clear your sessions, so sessions list in your phone will not grow big.

### Validating and decrypting messages
Now that you have the two keys, validating and decrypting messages the server sent to you is quite easy. Note that this is only needed for _binary_ messages, all JSON you receive stays plain. The binary messages always have 32 bytes at the beginning that specify the HMAC checksum. Both JSON _and_ binary messages have a message tag at their very start that can be discarded, i.e. only the portion after the first comma character is significant.

1. Validate the message by hashing the actual message content with the `macKey` (here `messageContent` is the _entire_ binary message): `HmacSha256(macKey, messageContent[32:])`. If this value is not equal to `messageContent[:32]`, the message sent to you by the server is invalid and should be discarded.
2. Decrypt the message content using AES and the `encKey`: `AESDecrypt(encKey, messageContent[32:])`.

The data you get in the final step has a binary format which is described in the following. Even though it's binary, you can still see several strings in it, especially the content of messages you sent is quite obvious there.

## Binary message format
### Binary decoding
The Python script `backend/decoder.py` implements the `MessageParser` class. It is able to create a JSON structure out of binary data in which the data is still organized in a rather messy way. The section about Node Handling below will discuss how the nodes are reorganized afterwards.

`MessageParser` initially just needs some data and then processes it byte by byte, i.e. as a stream. It has a couple of constants and a lot of methods which all build on each other.

#### Constants
- _Tags_ with their respective integer values
	- _LIST_EMPTY_: 0
	- _STREAM_8_: 2
	- _DICTIONARY_0_: 236
	- _DICTIONARY_1_: 237
	- _DICTIONARY_2_: 238
	- _DICTIONARY_3_: 239
	- _LIST_8_: 248
	- _LIST_16_: 249
	- _JID_PAIR_: 250
	- _HEX_8_: 251
	- _BINARY_8_: 252
	- _BINARY_20_: 253
	- _BINARY_32_: 254
	- _NIBBLE_8_: 255
- _Tokens_ are a long list of 151 strings in which the indices matter:
	- `[None,None,None,"200","400","404","500","501","502","action","add",
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
 "unsubscribe","disable"]`

#### Number reformatting
- _Unpacking nibbles_: Returns the ASCII representation for numbers between 0 and 9. Returns `-` for 10, `.` for 11 and `\0` for 15.
- _Unpacking hex values_: Returns the ASCII representation for numbers between 0 and 9 or letters between A and F (i.e. uppercase) for numbers between 10 and 15.
- _Unpacking bytes_: Expects a tag as an additional parameter, namely _NIBBLE_8_ or _HEX_8_. Unpacks a nibble or hex value accordingly.

#### Number formats

- _Byte_: A plain ol' byte.
- _Integer with N bytes_: Reads N bytes and builds a number out of them. Can be little or big endian; if not specified otherwise, big endian is used. Note that no negative values are possible.
- _Int16_: An integer with two bytes, read using _Integer with N bytes_.
- _Int20_: Consumes three bytes and constructs an integer using the last four bits of the first byte and the entire second and third byte. Is therefore always big endian.
- _Int32_: An integer with four bytes, read using _Integer with N bytes_.
- _Int64_: An integer with eight bytes, read using _Integer with N bytes_.
- _Packed8_: Expects a tag as an additional parameter, namely _NIBBLE_8_ or _HEX_8_. Returns a string.
	- First reads a byte `n` and does the following `n&127` many times: Reads a byte `l` and for each nibble, adds the result of its _unpacked version_ to the return value (using _unpacking bytes_ with the given tag). Most significant nibble first.
	- If the most significant bit of `n` was set, removes the last character of the return value.

#### Helper methods
- _Read bytes_: Reads and returns the specified number of bytes.
- _Check for list tag_: Expects a tag as parameter and returns true if the tag is `LIST_EMPTY`, `LIST_8` or `LIST_16` (i.e. 0, 248 or 249).
- _Read list size_: Expects a list tag as parameter. Returns 0 for `LIST_EMPTY`, returns a read byte for `LIST_8` or a read _Int16_ for `LIST_16`.
- _Read a string from characters_: Expects the string length as parameter, reads this many bytes and returns them as a string.
- _Get a token_: Expects an index to the array of _Tokens_, and returns the respective string.
- _Get a double token_: Expects two integers `a` and `b` and gets the token at index `a*256+b`.

#### Strings

Reading a string needs a _tag_ as parameter. Depending on this tag, different data is read.

- If the tag is between 3 and 235, the _token_ (i.e. a string) of this tag is got. If the token is `"s.whatsapp.net"`, `"c.us"` is returned instead, otherwise the token is returned as is.
- If the tag is between _DICTIONARY_0_ and _DICTIONARY_3_, a _double token_ is returned, with `tag-DICTIONARY_0` as first and a read byte as second parameter.
- _LIST_EMPTY_: Nothing is returned (e.g. `None`).
- _BINARY_8_: A byte is read which is then used to _read a string from characters_ with this length.
- _BINARY_20_: An _Int20_ is read which is then used to _read a string from characters_ with this length.
- _BINARY_32_: An _Int32_ is read which is then used to _read a string from characters_ with this length.
- _JID_PAIR_
	- First, a byte is read which is then used to _read a string_ `i` with this tag.
	- Second, another byte is read which is then used to _read a string_ `j` with this tag.
	- Finally, `i` and `j` are joined together with an `@` sign and the result is returned.
- _NIBBLE_8_ or _HEX_8_: A _Packed8_ with this tag is returned.

#### Attribute lists

Reading an attribute list needs the number of attributes to read as parameter. An attribute list is always a JSON object. For each attribute read, the following steps are executed for getting key-value pairs (exactly in this order!):
- _Key_: A byte is read which is then used to _read a string_ with this tag.
- _Value_: A byte is read which is then used to _read a string_ with this tag.

#### Nodes

A node always consists of a JSON array with exactly three entries: description, attributes and content. The following steps are needed to read a node:

1. A _list size_ `a` is read by using a read byte as the tag. The list size 0 is invalid.
2. The description tag is read as a byte. The value 2 is invalid for this tag. The description string `descr` is then obtained by _reading a string_ with this tag.
3. The attributes object `attrs` is read by _reading an attributes object_ with length `(a-2 + a%2) >> 1`.
4. If `a` was odd, this node does not have any content, i.e. `[descr, attrs, None]` is returned.
5. For getting the node's content, first a byte, i.e. a tag is read. Depending on this tag, different types of content emerge:
	- If the tag is a _list tag_, a _list is read_ using this tag (see below for lists).
	- _BINARY_8_: A byte is read which is then used as length for _reading bytes_.
	- _BINARY_20_: An _Int20_ is read which is then used as length for _reading bytes_.
	- _BINARY_32_: An _Int32_ is read which is then used as length for _reading bytes_.
	- If the tag is something else, a _string is read_ using this tag.
6. Eventually, `[descr, attrs, content]` is returned.

#### Lists

Reading a list requires a _list tag_ (i.e. _LIST_EMPTY_, _LIST_8_ or _LIST_16_). The length of the list is then obtained by _reading a list size_ using this tag. For each list entry, a _node is read_.

### Node Handling

After a binary message has been transformed into JSON, it is still rather hard to read. That's why, internally, WhatsApp Web completely retransforms this structure into something that can be easily processed and eventually translated into user interface content. This section will deal with this and awaits completion.

## Binary conversation format

When a node has been read, the contents of messages that have been actually sent by the user (i.e. text, image, audio, video etc.) are still not directly visible or accessible via the JSON. Instead, they are kept in a protobuf message. See [here](https://github.com/sigalor/whatsapp-web-reveng/blob/master/doc/spec/def.proto) for the definitions. The "wrapper" message type is `WebMessageInfo`.

## WhatsApp Web API
WhatsApp Web itself has an interesting API as well. You can even try it out directly in your browser. Just log in at the normal [https://web.whatsapp.com/](https://web.whatsapp.com/), then open the browser development console. Now enter something like the following (see below for details on the chat identification):

- `window.Store.Wap.profilePicFind("49123456789@c.us").then(res => console.log(res));`
- `window.Store.Wap.lastseenFind("49123456789@c.us").then(res => console.log(res));`
- `window.Store.Wap.statusFind("49123456789@c.us").then(res => console.log(res));`

Using the amazing Chrome developer console, you can see that `window.Store.Wap` contains a lot of other very interesting functions. Many of them return JavaScript promises. When you click on the _Network_ tab and then on _WS_ (maybe you need to reload the site first), you can look at all the communication between WhatsApp Web and its servers.

### Chat identification / JID
The WhatsApp Web API uses the following formats to identify chats with individual users and groups of multiple users.

- **Chats**: `[country code][number]@c.us`, e.g. **`49123456789@c.us`** when you are from Germany and your phone number is `0123 456789`.
- **Groups**: `[phone number of group creator]-[timestamp of group creation]@g.us`, e.g. **`49123456789-1509911919@g.us`** for the group that `49123456789@c.us` created on November 5 2017.
- **Broadcast Channels** `[timestamp of broadcast channel creation]@broadcast`, e.g. **`1509911919@broadcast`** for an broadcast channel created on November 5 2017.

### WebSocket messages
There are two types of WebSocket messages that are exchanged between server and client. On the one hand, plain JSON that is rather unambiguous (especially for the API calls above), on the other hand encrypted binary messages.

Unfortunately, these binary ones cannot be looked at using the Chrome developer tools. Additionally, the Python backend, that of course also receives these messages, needs to decrypt them, as they contain encrypted data. The section about encryption details discusses how it can be decrypted.

## Dealing with E2E media
### Encryption
1. Generate your own `mediaKey`, which needs to be 32 bytes.
2. Expand it to 112 bytes using HKDF with type-specific application info (see below). Call this value `mediaKeyExpanded`.
3. Split `mediaKeyExpanded` into:
	- `iv`: `mediaKeyExpanded[:16]`
	- `cipherKey`: `mediaKeyExpanded[16:48]`
	- `macKey`: `mediaKeyExpanded[48:80]`
	- `refKey`: `mediaKeyExpanded[80:]` (not used)
4. Encrypt the file with AES-CBC using `cipherKey` and `iv`, pad it and call it `enc`. 
5. Sign `iv + enc` with `macKey` using HMAC SHA-256 and store the first 10 bytes of the hash as `mac`.
6. Hash the file with SHA-256 and store it as `fileSha256`, hash the `enc + mac` with SHA-256 and store it as `fileEncSha256`.
7. Encode the `fileEncSha256` with base64 and store it as `fileEncSha256B64`.
8. This step is required only for streamable media, e.g. video and audio. As CBC mode allows to decrypt a data from random offset (block-size aligned), it is possible to play and seek the media without the need to fully download it. That said, we need to generate a `sidecar`. Do it by signing every `[n*64K, (n+1)*64K+16]` chunk with `macKey`, truncating the result to the first 10 bytes. Then combine everything in one piece.

### Upload
8. Retrieve the upload-url by sending `messageTag,["action", "encr_upload", filetype, fileEncSha256B64]`
	- `filetype` can be one of `image`, `audio`, `document` or `video`
9. Create a multipart-form with the following fields:
	- fieldname: `hash`: `fileEncSha256B64`
	- fieldname: `file`, filename: `blob`: `enc+mac`  
10. Do a POST request to the url with query string `?f=j` and the correct `content-type` and the multipart-form, WhatsApp will respond with the download url for the file.
11. All relevant information to send the file are now generated, just build the proto and send it.

### Decryption
1. Obtain `mediaKey` and decode it from Base64 if necessary.
2. Expand it to 112 bytes using HKDF with type-specific application info (see below). Call this value `mediaKeyExpanded`.
3. Split `mediaKeyExpanded` into:
	- `iv`: `mediaKeyExpanded[:16]`
	- `cipherKey`: `mediaKeyExpanded[16:48]`
	- `macKey`: `mediaKeyExpanded[48:80]`
	- `refKey`: `mediaKeyExpanded[80:]` (not used)
4. Download media data from the `url` and split it into:
	- `file`: `mediaData[:-10]`
	- `mac`: `mediaData[-10:]`
5. Validate media data with HMAC by signing `iv + file` with `macKey` using SHA-256. Take in mind that `mac` is truncated to 10 bytes, so you should compare only the first 10 bytes.
6. Decrypt `file` with AES-CBC using `cipherKey` and `iv`, and unpad it. Note that this means that your session's keys (i.e. `encKey` and `macKey` from the _Key generation_ section) are not necessary to decrypt a media file.

### Application info for HKDF
Depending on the media type, the literal strings in the right column are the values for the `appInfo` parameter from the [`HKDF` function](https://github.com/sigalor/whatsapp-web-reveng/blob/master/backend/whatsapp.py#L37).

| Media Type | Application Info         |
| ---------- | ------------------------ |
| IMAGE      | `WhatsApp Image Keys`    |
| VIDEO      | `WhatsApp Video Keys`    |
| AUDIO      | `WhatsApp Audio Keys`    |
| DOCUMENT   | `WhatsApp Document Keys` |

## Extending the web app's capabilities  

### Adding own commands

The message forwarding procedures are rather complex, as there are several layers of websockes involved in the process. For adding your own commands, follow these steps.

1. First, decide on what the final destination of your command shall be. To be consistent with the other, please prefix it with `backend_` if it's meant to be received by the Python backend or use `api_` if the command is directed to the NodeJS API.
2. Now, look at [`client/js/main.js`](https://github.com/sigalor/whatsapp-web-reveng/blob/master/client/js/main.js). In [line 214](https://github.com/sigalor/whatsapp-web-reveng/blob/master/client/js/main.js#L214), you can see an instantiation of the `BootstrapStep` JavaScript class. It needs the following information:
	-  `websocket`: is probably always the same
	-  `request.type`: should generally be `call`, as this allows a response to be passed back to the command's sender
	-  `request.callArgs`: an object which has to contain a `command` attribute specifying the name of your command and as many additional key-value-pairs as you want. All of these will be passed to the receiver.
	-  `request.successCondition`: on receiving a response for a call, this shall be a function returning `true` when the response is valid/expected. Use the next attribute for specifying code to be executed when the response is valid.
	-  `request.successActor`: when the success condition evaluated to `true`, this success actor function is called

	When the `BootstrapStep` object has been constructed, call `.run()` for running indefinitely or `.run(timeout_ms)` for failing when no response has been received after a specific timeout. The `run` function returns a Promise.
3. Next, edit [`index.js`](https://github.com/sigalor/whatsapp-web-reveng/blob/master/index.js). It contains a couple of blocks beginning with `clientWebsocket.waitForMessage`. You can copy one of these blocks and edit the parameters. The `waitForMessage` function needs the following attributes:
	-  `condition`: when a message is received and this condition evaluates to `true` on it, the message will be processed by the following `.then(...)` block
	-  `keepWhenHit`: it is possible for a message handler to be detached immediately after it receives its first fitting message. Control this here.
	The returned promise's `then` block finally handles a received message. It gets a `clientCallRequest` you can call `.respond({...})` on to send a JSON response to the caller. If the NodeJS API is not the message's final destination, you need to instantiate a new `BootstrapStep` here which will contact to the Python backend and, after it receives its response, will return it to the original caller.
4. Thus, when you want a message for the backend, now edit [`backend/whatsapp-web-backend.py`](https://github.com/sigalor/whatsapp-web-reveng/blob/master/backend/whatsapp-web-backend.py). In the if-else-compound starting in [line 88](https://github.com/sigalor/whatsapp-web-reveng/blob/master/backend/whatsapp-web-backend.py#L88), add your own branch for the command name you chose. Then, edit [`backend/whatsapp.py`](https://github.com/sigalor/whatsapp-web-reveng/blob/master/backend/whatsapp.py) and add a function similar to `generateQRCode` in [line 223](https://github.com/sigalor/whatsapp-web-reveng/blob/master/backend/whatsapp.py#L223). Just using something like in [`getLoginInfo`](https://github.com/sigalor/whatsapp-web-reveng/blob/master/backend/whatsapp.py#L230) may not be enough, as your command may require an asynchronous request to the WhatsApp Web servers. In this case, make sure to add an entry to `self.messageQueue` with the message tag you chose and send an appropriate message to `self.activeWs`. The servers will respond to your request with a response containing the same tag, thus this is resolved in [line 134](https://github.com/sigalor/whatsapp-web-reveng/blob/master/backend/whatsapp.py#L134). Make sure to eventually call `pend["callback"]["func"]({...})` with the JSON object containing your response data to resolve the callback.

## Docker

**Please note, this version is not stable enough to be deployabled in production.**

### Build docker image
`docker build . -t whatsapp-web-reveng`
### Run your image and redirect front & back ports
`docker run -p 2019:2019 -p 2018:2018 whatsapp-web-reveng`

Front end (client) at : <http://localhost:2018/>

### For server use
The addresses of the websockets used are "localhost" by default.
If you want to deploy this docker on your own server and share it, modify the backend websocket address on the front end. 
`client/js/main.js`
```javascript
let backendInfo = {
    url: "ws://{{your-server-addr}}:2020",
    timeout: 10000
};
```
Front end (client) at : : <http://{{your-server-addr}}:2018/>

## Tasks

### Backend

- [ ] More and more errors start to occur in the binary message decoding. Update this documentation to resemble the changes, then implement them.
- [ ] Allow sending messages as well. Of course JSON is easy, but _writing_ the binary message format needs to start being examined.

### Web frontend

- [ ] Allow reusing the session after successful login. Probably normal cookies are best for this. See [#9](https://github.com/sigalor/whatsapp-web-reveng/issues/9) for details.
- [ ] An UI that is not that technical, but rather starts to emulate the actual WhatsApp Web UI.

### General development

- [ ] Allow usage on Windows, i.e. entirely fix [#16](https://github.com/sigalor/whatsapp-web-reveng/issues/16).

### Documentation
- [ ] The _Node Handling_ section. Could become very long.
- [ ] Outsource the different documentation parts into their own files, maybe into the `gh-pages` branch.


## Legal
This code is in no way affiliated with, authorized, maintained, sponsored or endorsed by WhatsApp or any of its affiliates or subsidiaries. This is an independent and unofficial software. Use at your own risk.

## Cryptography Notice
This distribution includes cryptographic software. The country in which you currently reside may have restrictions on the import, possession, use, and/or re-export to another country, of encryption software. BEFORE using any encryption software, please check your country's laws, regulations and policies concerning the import, possession, or use, and re-export of encryption software, to see if this is permitted. See [http://www.wassenaar.org/](http://www.wassenaar.org/) for more information.

The U.S. Government Department of Commerce, Bureau of Industry and Security (BIS), has classified this software as Export Commodity Control Number (ECCN) 5D002.C.1, which includes information security software using or performing cryptographic functions with asymmetric algorithms. The form and manner of this distribution makes it eligible for export under the License Exception ENC Technology Software Unrestricted (TSU) exception (see the BIS Export Administration Regulations, Section 740.13) for both object code and source code.
