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
![whatsapp-web-reveng Application architecture](https://i.stack.imgur.com/CjZ8v.png)


## Encryption details
WhatsApp Web encrypts the data using several different algorithms. These include [AES 256 ECB](https://en.wikipedia.org/wiki/Advanced_Encryption_Standard), [Curve25519](https://en.wikipedia.org/wiki/Curve25519) as Diffie-Hellman key agreement scheme, [HKDF](https://en.wikipedia.org/wiki/HKDF) for generating the extended shared secret and [HMAC](https://en.wikipedia.org/wiki/Hash-based_message_authentication_code) with SHA256.

This section will be completed with more detailed information later.

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
