if(typeof window === 'undefined') {
    let updater_promise = require("./UpdaterPromise.js");		//apparently it really needs to be *that* ugly
    UpdaterPromise = updater_promise.UpdaterPromise;
}

class WebSocketClient {
    constructor(url, whoami) {
        this.info = {
            errors: {
                basic: {
                    timeout: "Timeout",
                    connectionFailed: "Connection failed",
                    invalidResponse: "Invalid response",
                }
            }
        };
        if(url != undefined  &&  whoami != undefined)
            initialize(url, whoami);
    }

    _initializeWebSocketListeners() {
        this.isOpen = false;
        this.ws.onmessage = msg => {
            let actualMsg = this.constructorConfig.getOnMessageData ? this.constructorConfig.getOnMessageData(msg) : msg;
            let tag = actualMsg.split(",")[0];
            let obj = JSON.parse(actualMsg.substr(tag.length + 1));
            console.log("got message ", obj);

            let idx = this.expectedMsgs.findIndex(e => e.condition(obj, tag));
            if(idx != -1) {
                let currMsg = this.expectedMsgs[idx].keepWhenHit ? this.expectedMsgs[idx] : this.expectedMsgs.splice(idx, 1)[0];
                //if(!currMsg.keepWhenHit)
                //	console.log("just removed ", currMsg.condition.toString(), " from expectedMsgs");
                //console.log("resolving ", obj, " to index ", idx);
                currMsg.resolve({
                    data: obj,
                    respond: obj => this.send(obj, tag)
                });
            }
        };
        this.ws.onopen = () => {
            this.simulateMsg({ from: "meta", type: "opened" });
            this.isOpen = true;
        };
        this.ws.onclose = () => {
            this.simulateMsg({ from: "meta", type: "closed" });
            this.isOpen = false;
        }
    }

    initialize(url, whoami, constructorConfig) {
        this.expectedMsgs = [];
        this.whoami = whoami;
        this.constructorConfig = constructorConfig;
        try {
            this.ws = new this.constructorConfig.func(url, ...(this.constructorConfig.args || []));
        }
        catch(e) {
            throw this.info.errors.basic.connectionFailed;
        }
        this._initializeWebSocketListeners();
        return this;
    }

    initializeFromRaw(ws, whoami, constructorConfig) {
        this.expectedMsgs = [];
        this.whoami = whoami;
        this.constructorConfig = constructorConfig;
        this.ws = ws;
        this._initializeWebSocketListeners();
        return this;
    }

    simulateMsg(obj) {
        let msgTag = +new Date();
        this.ws.onmessage({ data: `${msgTag},${JSON.stringify(obj)}` })
    }

    send(obj, tag) {
        return new Promise((resolve, reject) => {
            let msgTag = tag==undefined ? (+new Date()) : tag;
            this.waitForMessage({
                condition: (obj, tag) => tag == msgTag,
                keepWhenHit: false
            })
            .then((...args) => { resolve(...args); })
            .catch((...args) => reject(...args));
            if(obj.from == undefined)
                obj.from = this.whoami;
            this.ws.send(`${msgTag},${JSON.stringify(obj)}`);
        });
    }

    waitForMessage({condition, keepWhenHit, timeoutCondition, timeout}) {
        let executor = (resolve, reject) => {
            let timedOut = false, currTimeout;
            if(timeout != undefined) {
                currTimeout = setTimeout(() => {
                    timedOut = true;
                    if(this.isOpen  &&  (timeoutCondition == undefined  ||  timeoutCondition(this)))
                        reject(this.info.errors.basic.timeout);
                }, timeout);
            }

            this.expectedMsgs.push({
                condition: condition,
                keepWhenHit: keepWhenHit,
                resolve: (...args) => {
                    if(timedOut)
                        return;
                    clearTimeout(currTimeout);
                    resolve(...args);
                },
                reject: (...args) => {
                    if(timedOut)
                        return;
                    clearTimeout(currTimeout);
                    reject(...args);
                }
            });
            //console.log("index ", this.expectedMsgs.length-1, ": registered waitForMessage on", this.whoami, "with condition ", condition.toString());
        }
        return (keepWhenHit ? new UpdaterPromise(executor) : new Promise(executor));
    }

    call({callArgs, successCondition, successActor, failureActor, timeoutCondition, timeout}) {
        return new Promise((resolve, reject) => {
            let msgTag = +new Date();
            this.waitForMessage({
                condition: (obj, tag) => tag == msgTag,
                keepWhenHit: false,
                timeoutCondition: timeoutCondition,
                timeout: timeout
            })
            .then((...args) => {
                if(successCondition(args[0].data)) {
                    if(successActor != undefined)
                        successActor(this, args[0].data);
                    resolve(...args);
                }
                else
                    reject(args[0].data.type == "error" ? args[0].data.reason : this.info.errors.basic.invalidResponse);
            })
            .catch((...args) => {
                if(failureActor != undefined)
                    failureActor(this, args[0]);
                reject(...args);
            });

            let obj = Object.assign(callArgs, { from: this.whoami, type: "call" });
            this.ws.send(`${msgTag},${JSON.stringify(obj)}`);
        });
    }

    onClose(callback) {
        this.waitForMessage({
            condition: obj => obj.from == "meta"  &&  obj.type == "closed",
            keepWhenHit: false
        }).then((...args) => callback(...args));
    }

    disconnect() {
        console.log("disconnecting " + this.whoami, this.isOpen);
        if(this.isOpen)
            this.ws.close();
    }
}

if(typeof window === 'undefined')
    exports.WebSocketClient = WebSocketClient;
