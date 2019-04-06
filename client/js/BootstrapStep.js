class BootstrapStep {
    constructor({websocket, texts, actor, request}) {
        this.websocket = websocket;
        this.texts = texts;
        this.actor = actor;
        this.request = request;
    }

    run(timeout) {
        return new Promise((resolve, reject) => {
            if(this.actor != undefined)
                this.actor(this.websocket);

            let promise;
            switch(this.request.type) {
                case "waitForMessage": {
                    promise = this.websocket.waitForMessage({
                        condition: this.request.condition,
                        keepWhenHit: false,
                        timeout: timeout
                    });
                    break;
                }

                case "call": {
                    promise = this.websocket.call({
                        callArgs: this.request.callArgs,
                        ignoreCondition: this.request.ignoreCondition,
                        successCondition: this.request.successCondition,
                        successActor: this.request.successActor,
                        failureActor: this.request.failureActor,
                        timeoutCondition: this.request.timeoutCondition,
                        timeout: timeout
                    });
                    break;
                }
            }
            if(promise != undefined) {
                return promise.then((...args) => {
                    resolve(...args);
                })
                .catch((...args) => {
                    reject(...args);
                });
            }
        });
    }
}

if(typeof window === 'undefined')
    exports.BootstrapStep = BootstrapStep;
