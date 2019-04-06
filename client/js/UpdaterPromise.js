//just a promise class where the '.then(...)'-callback can be called any number of times
class UpdaterPromise {
    constructor(executor) {
        this.onFulfilled = () => {};
        this.onRejected = (...args) => console.error("unhandled promise rejection: ", ...args);
        this.executor = executor;
    }

    then(callback) {
        this.onFulfilled = callback;
        return this;
    }

    catch(callback) {
        this.onRejected = callback;
        return this;
    }

    run() {
        try      { this.executor(this.onFulfilled, this.onRejected); }
        catch(e) { this.onRejected(e); }
        return this;
    }
}

if(typeof window === 'undefined')										//from https://stackoverflow.com/a/4224668
    exports.UpdaterPromise = UpdaterPromise;
