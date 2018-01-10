
# WhatsApp Web reverse engineered

## Introduction
This project intends to provide a complete description and re-implementation of the WhatsApp Web API, which will eventually lead to a custom client. WhatsApp Web internally works using WebSockets; this project does as well.

## Trying it out
Before you can run the application, make sure that you have the following software installed:

- Node.js (at least version 8, as the `async` `await` syntax is used)
- the CSS preprocessor [Sass](http://sass-lang.com/) (which you previously need Ruby for)
- Python 2.7 with the following `pip` packages installed:
  - `websocket-client` and `git+https://github.com/dpallot/simple-websocket-server.git` for acting as WebSocket server and client
  - `curve25519-donna` and `pycrypto` for the encryption stuff
  - `pyqrcode` for QR code generation
 
Before starting the application for the first time, run `npm install` to install all dependencies.

Lastly, to finally launch it, just run `npm start`. Using fancy `concurrently` and `nodemon` magic, all three local components will be started after each other and when you edit a file, the changed module will automatically restart to apply the changes.

## Application architecture
The project is organized in the following way. Note the used ports and make sure that they are not in use elsewhere before starting the application.
![whatsapp-web-reveng Application architecture](https://raw.githubusercontent.com/sigalor/whatsapp-web-reveng/master/doc/img/app-architecture1000.png)


## Login and encryption details
WhatsApp Web encrypts the data using several different algorithms. These include [AES 256 ECB](https://en.wikipedia.org/wiki/Advanced_Encryption_Standard), [Curve25519](https://en.wikipedia.org/wiki/Curve25519) as Diffie-Hellman key agreement scheme, [HKDF](https://en.wikipedia.org/wiki/HKDF) for generating the extended shared secret and [HMAC](https://en.wikipedia.org/wiki/Hash-based_message_authentication_code) with SHA256.

Starting the WhatsApp Web session happens by just connecting to one of its websocket servers at `wss://w[1-8].web.whatsapp.com/ws` (`wss://` means that the websocket connection is secure; `w[1-8]` means that any number between 1 and 8 can follow the `w`). Also make sure that, when establishing the connection, the HTTP header `Origin: https://web.whatsapp.com` is set, otherwise the connection will be rejected.

### Messages
When you send messages to a WhatsApp Web websocket, they need to be in a specific format. It is quite simple and looks like `messageTag,JSON`, e.g. `1515590796,["data",123]`. Note that apparently the message tag can be anything. This application mostly uses the current timestamp as tag, just to be a bit unique. WhatsApp itself often uses message tags like `s1`, `1234.--0` or something like that. Obviously the message tag may not contain a comma. Additionally, JSON _objects_ are possible as well as payload.

### Logging in
To log in at an open websocket, follow these steps:

1. Generate your own `clientId`, which needs to be 16 base64-encoded bytes (i.e. 25 characters). This application just uses 16 random bytes, i.e. `base64.b64encode(os.urandom(16))` in Python.
2. Decide for a tag for your message, which is more or less arbitrary (see above). This application uses the current timestamp (in seconds) for that. Remember this tag for later.
3. The message you send to the websocket looks like this: `messageTag,["admin","init",[0,2,7314],["Long browser description","ShortBrowserDesc"],"clientId",true]`.
	- Obviously, you need to replace `messageTag` and `clientId` by the values you chose before
	- The `[0,2,7314]` part specifies the current WhatsApp Web version. The last value changes frequently. It should be quite backwards-compatible though.
	- `"Long browser description"` is an arbitrary string that will be shown in the WhatsApp app in the list of registered WhatsApp Web clients after you scan the QR code.
	- `"ShortBrowserDesc"` has not been observed anywhere yet but is arbitrary as well.
4. After a few moments, your websocket will receive a message in the specified format with the message tag _you chose in step 2_. The JSON object of this message has the following attributes:
	- `status`: should be 200
	- `ref`: in the application, this is treated as the server ID; important for the QR generation, see below
	- `ttl`: is 20000, maybe the time after the QR code becomes invalid
	- `update`: false
	- `curr`: the current WhatsApp Web version, e.g. `0.2.7314`
	- `time`: the timestamp the server responded on, as floating-point milliseconds, e.g. `1515592039037.0`

### QR code generation
5. Generate your own private key with Curve25519, e.g. `curve25519.Private()`.
6. Get the public key from your private key, e.g. `privateKey.get_public()`.
7. Obtain the string later encoded by the QR code by concatenating the following values with a comma:
	- the server ID, i.e. the `ref` attribute from step 4
	- the base64-encoded version of your public key, i.e. `base64.b64encode(publicKey.serialize())`
	- your client ID
8. Turn this string into an image (e.g. using `pyqrcode`) and scan it using the WhatsApp app.

### After scanning the QR code
9. Immediately after you scan the QR code, the websocket received several important JSON messages that build up the encryption details. These use the specified message format and have a JSON _array_ as payload. Their message tag has no special meaning. The second entry is an object. The first entry of the JSON array has one of the following values:
	- `Conn`: array contains JSON object as second element with connection information containing the following attributes and many more:
		- `battery`: the current battery percentage of your phone
		- `browserToken` (could be important, but not used by the application yet)
		- `clientToken` (could be important, but not used by the application yet)
		- `phone`: an object with detailed information about your phone, e.g. `device_manufacturer`, `device_model`, `os_build_number`, `os_version`
		- `platform`: your phone OS, e.g. `android`
		- `pushname`: the name of yours you provided WhatsApp
		- `secret` (remember this!)
		- `serverToken` (could be important, but not used by the application yet)
		- `wid`: your phone number in the chat identification format (see below)
	- `Stream`: array has four elements in total, so the entire payload is like `["Stream","update",false,"0.2.7314"]`
	- `Props`: array contains JSON object as second element with several properties like `imageMaxKBytes` (1024), `maxParticipants` (257), `videoMaxEdge` (960) and others

### Key generation
10. You are now ready for generating the final encryption keys. Start by decoding the `secret` from `Conn` as base64 and storing it as `secret`. This decoded secret will be 144 bytes long.
11. Take the _first 32 bytes_ of the decoded secret and use it as a public key. Together with your private key, generate a shared key out of it and call it `sharedSecret`. The application does it using `privateKey.get_shared_key(curve25519.Public(secret[:32]), lambda a:a)`.
12. Encode a message containing 32 null bytes with the shared secret using HMAC SHA256. Take this value and extend it to 80 bytes using HKDF. Call this value `sharedSecretExpanded`. This is done with `HKDF(HmacSha256("\0"*32, sharedSecret), 80)`.
13. This step is optional, it validates the data provided by the server. The method is called _HMAC validation_. Do it by first calculating `HmacSha256(sharedSecretExpanded[32:64], secret[:32] + secret[64:])`. Compare this value to `secret[32:64]`. If they are not equal, abort the login.
14. You now have the encrypted keys: store `sharedSecretExpanded[64:] + secret[64:]` as `keysEncrypted`.
15. The encrypted keys now need to be decrypted using AES with `sse[:32]` as key, i.e. store `AESDecrypt(sharedSecretExpanded[:32], keysEncrypted)` as `keysDecrypted`.
16. The `keysDecrypted` variable is 64 bytes long and contains two keys, each 32 bytes long. The `encKey` is used for decrypting binary messages sent to you by the WhatsApp Web server or encrypting binary messages you send to the server. The `macKey` is needed to validate the messages sent to you:
	- `encKey`: `keysDecrypted[:32]`
	- `macKey`: `keysDecrypted[32:64]`

### Validating and decrypting messages
Now that you have the two keys, validating and decrypting messages the server sent to you is quite easy. Note that this is only needed for _binary_ messages, all JSON you receive stays plain. The binary messages always have 32 bytes at the beginning that specify the HMAC checksum.

1. Validate the message by hashing the actual message content with the `macKey` (here `messageContent` is the _entire_ binary message): `HmacSha256(macKey, messageContent[32:])`. If this value is not equal to `messageContent[:32]`, the message sent to you by the server is invalid and should be discarded.
2. Decrypt the message content using AES and the `encKey`: `AESDecrypt(encKey, messageContent[32:])`.

The data you get in the final step has a binary format which is described in the following. Even though it's binary, you can still see several strings in it, especially the content of messages you sent is quite obvious there.

### Binary message format

This section will be completed later.

## WhatsApp Web API
WhatsApp Web itself has an interesting API as well. You can even try it out directly in your browser. Just log in at the normal [https://web.whatsapp.com/](https://web.whatsapp.com/), then open the browser development console. Now enter something like the following (see below for details on the chat identification):

- `window.Store.Wap.profilePicFind("49123456789@c.us").then(res => console.log(res));`
- `window.Store.Wap.lasteenFind("49123456789@c.us").then(res => console.log(res));`
- `window.Store.Wap.statusFind("49123456789@c.us").then(res => console.log(res));`

Using the amazing Chrome developer console, you can see that `window.Store.Wap` contains a lot of other very interesting functions. Many of them return JavaScript promises. When you click on the _Network_ tab and then on _WS_ (maybe you need to reload the site first), you can look at all the communication between WhatsApp Web and its servers.

### Chat identification
The WhatsApp Web API uses the following formats to identify chats with individual users and groups of multiple users.

- **Chats**: `[country code][number]@c.us`, e.g. **`49123456789@c.us`** when you are from Germany and your phone number is `0123 456789`.
- **Groups**: `[phone number of group creator]-[timestamp of group creation]@g.us`, e.g. **`49123456789-1509911919@g.us`** for the group that `49123456789@c.us` created on November 5 2017.

### WebSocket messages
There are two types of WebSocket messages that are exchanged between server and client. On the one hand, plain JSON that is rather unambiguous (especially for the API calls above), on the other hand encrypted binary messages.

Unfortunately, these cannot be looked at using the Chrome developer tools. Additionally, the Python backend, that of course also receives these messages, needs to decrypt them, as they contain encrypted data. The section about encryption details discusses how it can be decrypted.
