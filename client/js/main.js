let consoleShown = false;
let apiWebsocket = new WebSocketClient();

function sleep(ms) {
    return new Promise((resolve, reject) => {
        setTimeout(() => resolve(), ms);
    });
}

$(document).ready(function() {

    let is_full_view = false;
    let selected_user ;
    let page = 0 ;
    let contacts = {}
    let users = {}
    
    const axiosController = new AbortController();
    function clearStatuses()
    {
        users = {};
        app.$root.users = {};

        contacts = {};
        app.$root.contacts = {};

    }
    function setStatuses(data)
    {
        if(data.message_type == "jsonStatuses"){
                                
            users = data.message[2];
            app.$root.users = data.message[2];
            console.log(data.message[2])
        }
    }
    function setContacts(data)
    {
        if(data.message_type == "jsonContacts"){
            contacts = data.message[3];
            app.$root.contacts = data.message[3];
            console.log(data.message[3])

        }

    }
    var app = new Vue({
            el: '#app',
            data: {
                axiosController : axiosController,
                is_full_view : is_full_view,
                selected_user: selected_user,
                page: page,
                users : users,
            
            }
            ,
            methods: {
                getNameByJid: function (jid) {
                    return contacts[jid];
                    },
                getUserDataByJid: function (jid) {
                return users[jid];
                },
                getFirstMedia: function () {
                    if(selected_user)
                        return Object.values(this.getUserDataByJid(selected_user)[0])[0];
                }

                }
            });
    Vue.component('users-list', {
        props: ['user','num','name'],

        computed: {
            getImage: function()
            {
                textPlaceHolder = "iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAAAAXNSR0IArs4c6QAAAU5JREFUSEvtl79qAkEQhz+LNFYWElJYKHkDi6RLJb6IkJcK+B4WVjYBC18hRUIIwSKFRSCYMLIrc8vsundcFPGuuv33+2Zmd+fmWhSf36Bdd7PlBfcvrkPAYV9d8IK2hrSBTQCOReAK+FHGWsZNgKkaEK1r4FP6NPgeeFZ9HmpFpQusD4QiXC/tR+ApBL8DNw4sk16AgSEuYxos7QXwYMzdOj0xvmCI9kYPpPbaAr8BvUgEvFYSLF72nUDskFngJXCXAH8Dr8Ct30rLY1k/BFYJoZw99svHwExp7ZhVrk7ZUJv2N+CcLNWEWiKQusfN4dpF4Cyuk8654UfiX/f4ZGB/Oo9+j0/m8WWDO8CXKvY+XNmUk+tL32Md6ljJdFSwlKzicalkVGoyoKtG7Z1EYwTMc13OAYdFfaoI1Nykdi44Z55OMAe/AzmCVX/kktp/xJSEH1b13sIAAAAASUVORK5CYII=";
                return Object.values(this.user[0])[0]['jpegThumbnail'] == undefined ? textPlaceHolder : Object.values(this.user[0])[0]['jpegThumbnail']
            }
        },
        methods:
        {
            toggleFullView: function()
            {
                this.$root.is_full_view = this.$root.is_full_view  ? false : true;
                
            },
            setSelectedUser: function(num)
            {
                this.toggleFullView()
                this.$root.selected_user = num;
                this.$root.page = 1
            },

            getFirstMediaThumb: function(num)
            {
                this.$root.selected_user = num;
                this.$root.page = 1
            }

        },
        template: `
        <div class="user-item" :num="num" @click="setSelectedUser(num)">
                <div class="user-image" :style="'background-image: url(data:image/jpeg;base64,'+ getImage +');'" 
                >
                </div>
                <div class="user-details">
                    <span>{{name}}</span>
                    <span>{{moment(Object.values(user[0])[0]['mediaKeyTimestamp'], "X").fromNow()}}</span>
                </div>

            </div>
        `
        });
    Vue.component('dots', {
        props: ['count','page','index'],
        methods:
        {
            initStyle: function()
            {
                // console.log(this.page +" width:" +  100 / parseInt(this.count) + ";")
                return "width:" +  100 / parseInt(this.count) + "%;"
            },
            initClass: function()
            {
                if(parseInt(this.index) == parseInt(this.page))
                    return "active"
                return ""    
            },

        },
        template: `
            <div :class="'dots ' + initClass()" :style="initStyle()">
                
            </div>
        `
        });
    Vue.component('full-view', {
    props: ['user','num','media'],
    data: function () {
        return {
            base64Media: 'null',
            page: this.$root.page - 1,
            media : this.media,
            userLength : this.user.length,
            isLoading : true,
        }
    },
    created: function () {
        this.fetchFile()
    },
    methods:
        {
            fetchFile: function()
            {

                this.isLoading = true
                currentFile = Object.values(this.user[this.page])[0]
                this.media = currentFile

                if(this.media['text']){
                    return;
                }
                this.base64Media = this.media['jpegThumbnail']

                url = 'http://localhost:2018/downloadFile?mediakey='+encodeURIComponent(currentFile.mediaKey)+'&mimetype='+currentFile.mimetype
                +'&url='+ encodeURIComponent(currentFile.url);

                vm = this
                axios.get(url,{signal: this.$root.axiosController.signal})
                .then(function (response) {
                    vm.base64Media = response.data;
                    vm.isLoading = false
                                        
                })
                .catch(function (error) {
                    console.log(error)
                    vm.base64Media = undefined
                
                })


            },
            toggleFullView: function()
            {
                this.$root.is_full_view = false;
                this.$root.page = 0

                // abort media request before loading ends
                this.$root.axiosController.abort()
                this.$root.axiosController = new AbortController();

            },
            nextPage: function()
            {
                if(this.page + 1 < this.userLength){
                    this.page = this.page + 1
                    this.fetchFile()
                }else
                this.$root.is_full_view = false;

            },
            perviousPage: function()
            {
                if(this.page - 1 >= 0){
                    this.page = this.page - 1
                    this.fetchFile()
                }else
                    this.$root.is_full_view = false;

            },
        },

    template: `
        <div v-if="this.media.hasOwnProperty('text')" class="full-view" :num="num" :page="this.$root.page" >
            <div class="text-media">{{ this.media['text'] }}</div>
            <div class="close" @click="toggleFullView">X</div>
            <div v-if="this.page + 1 < this.userLength" class="next" @click="nextPage"></div>
            <div v-if="this.page - 1 >= 0 " class="pervious" @click="perviousPage"></div>
            <div class="status-dots"> <dots 
                v-for="(value, key) in this.user"
                v-bind:key="key"
                v-bind:count="userLength"
                v-bind:page="page"
                v-bind:index="key"

                ></dots>
            </div>

        </div>
        <div v-else-if="this.media.mimetype == 'image/jpeg'" class="full-view" :num="num" :page="this.$root.page" :style="'background-image: url(data:image/jpeg;base64,' + base64Media + ');'" >
            <div class="close" @click="toggleFullView">X</div>
            <div v-if="this.page + 1 < this.userLength" class="next" @click="nextPage"></div>
            <div v-if="this.page - 1 >= 0 " class="pervious" @click="perviousPage"></div>
            <div v-if="isLoading" class="loader"></div>
            <div class="status-dots"> <dots 
                v-for="(value, key) in this.user"
                v-bind:key="key"
                v-bind:count="userLength"
                v-bind:page="page"
                v-bind:index="key"

                ></dots>
            </div>
        </div>
        <div v-else-if="this.media.mimetype == 'video/mp4'" class="full-view" :num="num" :page="this.$root.page" >
            <video  controls :src="'data:video/mp4;base64,' + base64Media " autoplay :poster="'data:image/jpeg;base64,' + media['jpegThumbnail'] ">
            </video>

            <div class="close" @click="toggleFullView">X</div>
            <div v-if="this.page + 1 < this.userLength" class="next" @click="nextPage"></div>
            <div v-if="this.page - 1 >= 0 " class="pervious" @click="perviousPage"></div>
            <div v-show="isLoading" class="loader"></div>
            <div class="status-dots"> <dots 
                v-for="(value, key) in this.user"
                v-bind:key="key"
                v-bind:count="userLength"
                v-bind:page="page"
                v-bind:index="key"

                ></dots>
        </div>


    `
});










    $("#console-arrow-button").click(() => {
        if(consoleShown) {
            $("#console-arrow").removeClass("extended").find("i.fa").removeClass("fa-angle-right").addClass("fa-angle-left");
            $("#console").removeClass("extended");
        }
        else {
            $("#console-arrow").addClass("extended").find("i.fa").removeClass("fa-angle-left").addClass("fa-angle-right");
            $("#console").addClass("extended");
        }
        consoleShown = !consoleShown;
    });
    
    const responseTimeout = 10000;
    let bootstrapState = 0;
    


    let apiInfo = {
        url: "ws://localhost:2019",
        timeout: 10000,
        errors: {
            basic: {
                timeout: "Timeout",
                invalidResponse: "Invalid response"
            }
        }
    };



    let allWhatsAppMessages = [];
    let bootstrapInfo = {
        activateButton: (text, buttonEnabled) => {
            let container = $("#bootstrap-container").removeClass("hidden").children("#bootstrap-container-content");
            container.children("img").detach();
            container.children("button").removeClass("hidden").html(text).attr("disabled", !buttonEnabled);
            $("#main-container").addClass("hidden");

            allWhatsAppMessages = [];
            $("#messages-list-table-body").empty();
            $("#restore-session").addClass("hidden");

        },
        activateQRCode: image => {
            let container = $("#bootstrap-container").removeClass("hidden").children("#bootstrap-container-content");
            container.children("button").addClass("hidden")
            container.append($("<img>").attr("src", image));
            $("#main-container").addClass("hidden");
        },
        deactivate: () => {
            $("#bootstrap-container").addClass("hidden");
            $("#main-container").removeClass("hidden");
            $("#button-disconnect").html("Disconnect").attr("disabled", false);
        },
        restoreSession: () => {
            $("#restore-session").removeClass("hidden");
            $("#restore-session").html("Restore Session");

        },
        steps: [
            new BootstrapStep({
                websocket: apiWebsocket,
                texts: {
                    handling: "Connecting to API...",
                    success: "Connected to API after %1 ms. Click to let API connect to backend.",
                    failure: "Connection to API failed: %1. Click to try again.",
                    connLost: "Connection to API closed. Click to reconnect."
                },
                actor: websocket => {
                    websocket.initialize(apiInfo.url, "client", {func: WebSocket, getOnMessageData: msg => msg.data});
                    websocket.onClose(() => {
                        bootstrapInfo.activateButton(bootstrapInfo.steps[0].texts.connLost, true);
                        bootstrapState = 0;
                    });
                },
                request: {
                    type: "waitForMessage",
                    condition: obj => obj.type == "connected"
                }
            }),
            new BootstrapStep({
                websocket: apiWebsocket,
                texts: {
                    handling: "Connecting to backend...",
                    success: "Connected API to backend after %1 ms. Click to let backend connect to WhatsApp.",
                    failure: "Connection of API to backend failed: %1. Click to try again.",
                    connLost: "Connection of API to backend closed. Click to reconnect."
                },
                actor: websocket => {
                    websocket.waitForMessage({
                        condition: obj => obj.type == "resource_gone"  &&  obj.resource == "backend",
                        keepWhenHit: false
                    }).then(() => {
                        bootstrapInfo.activateButton(bootstrapInfo.steps[1].texts.connLost, true);
                        bootstrapState = 1;
                        websocket.apiConnectedToBackend = false;
                        websocket.backendConnectedToWhatsApp = false;
                        
                        // empty statuses
                        clearStatuses();
                    });
                },
                request: {
                    type: "call",
                    callArgs: { command: "api-connectBackend" },
                    successCondition: obj => obj.type == "resource_connected"  &&  obj.resource == "backend",
                    successActor: websocket => websocket.apiConnectedToBackend = true
                }
            }),
            new BootstrapStep({
                websocket: apiWebsocket,
                texts: {
                    handling: "Connecting to WhatsApp...",
                    success: "Connected backend to WhatsApp after %1 ms. Click to generate QR code.",
                    failure: "Connection of backend to WhatsApp failed: %1. Click to try again.",
                    connLost: "Connection of backend to WhatsApp closed. Click to reconnect."
                },
                actor: websocket => {
                    bootstrapInfo.restoreSession();

                    websocket.waitForMessage({
                        condition: obj => obj.type == "resource_gone"  &&  obj.resource == "whatsapp",
                        keepWhenHit: false
                    }).then(() => {
                        bootstrapInfo.activateButton(bootstrapInfo.steps[2].texts.connLost, true);
                        bootstrapState = 2;
                        websocket.backendConnectedToWhatsApp = false;

                        // empty statuses
                        clearStatuses();
                    });
                },
                request: {
                    type: "call",
                    callArgs: { command: "backend-connectWhatsApp" },
                    successCondition: obj => obj.type == "resource_connected"  &&  obj.resource == "whatsapp",
                    successActor: (websocket, obj) => websocket.backendConnectedToWhatsApp = true,
                    timeoutCondition: websocket => websocket.apiConnectedToBackend				//condition for the timeout to be possible at all (if connection to backend is closed, a timeout for connecting to WhatsApp shall not override this issue message)
                }
            }),
            new BootstrapStep({
                websocket: apiWebsocket,
                texts: {
                    handling: "Generating QR code...",
                    success: "Generated QR code after %1 ms.",
                    failure: "Generating QR code failed: %1. Click to try again."
                },
                request: {
                    type: "call",
                    callArgs: { command: "backend-generateQRCode" },
                    successCondition: obj => obj.type == "generated_qr_code"  &&  obj.image,
                    successActor: (websocket, {image}) => {
                        bootstrapInfo.activateQRCode(image);

                        websocket.waitForMessage({
                            condition: obj => obj.type == "whatsapp_message_received"  &&  obj.message,
                            keepWhenHit: true
                        }).then(whatsAppMessage => {
                            bootstrapInfo.deactivate();
                            /*<tr>
                                <th scope="row">1</th>
                                <td>Do., 21.12.2017, 22:59:09.123</td>
                                <td>Binary</td>
                                <td class="fill no-monospace"><button class="btn">View</button></td>
                            </tr>*/

                            let d = whatsAppMessage.data;
                            let viewJSONButton = $("<button></button>").addClass("btn").html("View").click(function() {
                                let messageIndex = parseInt($(this).parent().parent().attr("data-message-index"));
                                let jsonData = allWhatsAppMessages[messageIndex];
                                let tree, collapse = false;
                                let dialog = bootbox.dialog({
                                    title: `WhatsApp message #${messageIndex+1}`,
                                    message: "<p>Loading JSON...</p>",
                                    buttons: {
                                        noclose: {
                                            label: "Collapse/Expand All",
                                            className: "btn-info",
                                            callback: function () {
                                                if (!tree)
                                                    return true;

                                                if (collapse === false)
                                                    tree.expand();
                                                else
                                                    tree.collapse();

                                                collapse = !collapse;

                                                return false;
                                            }
                                        }
                                    }
                                });
                                dialog.init(() => {
                                    tree = jsonTree.create(jsonData, dialog.find(".bootbox-body").empty()[0]);
                                });
                            });

                            // set statuses
                            setStatuses(d);
                            // set contacts
                            setContacts(d);

                            let tableRow = $("<tr></tr>").attr("data-message-index", allWhatsAppMessages.length);
                            tableRow.append($("<th></th>").attr("scope", "row").html(allWhatsAppMessages.length+1));
                            tableRow.append($("<td></td>").html(moment.unix(d.timestamp/1000.0).format("ddd, DD.MM.YYYY, HH:mm:ss.SSS")));
                            tableRow.append($("<td></td>").html(d.message_type));
                            tableRow.append($("<td></td>").addClass("fill no-monospace").append(viewJSONButton));
                            $("#messages-list-table-body").append(tableRow);
                            allWhatsAppMessages.push(d.message);

                            //$("#main-container-content").empty();
                            //jsonTree.create(whatsAppMessage.data.message, $("#main-container-content")[0]);
                        }).run();
                    },
                    timeoutCondition: websocket => websocket.backendConnectedToWhatsApp
                }
            }),
            new BootstrapStep({
                websocket: apiWebsocket,
                texts: {
                    handling: "Restoring...",
                    success: "Restored in %1 ms.",
                    failure: "Restore failed: %1. Click to try again."
                },
                request: {
                    type: "call",
                    callArgs: { command: "backend-restoreSession" },
                    successCondition: obj => obj.type == "restore_session" ,
                    successActor: (websocket) => {
                        websocket.waitForMessage({
                            condition: obj => obj.type == "whatsapp_message_received"  &&  obj.message,
                            keepWhenHit: true
                        }).then(whatsAppMessage => {

                            bootstrapInfo.deactivate();
                            /*<tr>
                                <th scope="row">1</th>
                                <td>Do., 21.12.2017, 22:59:09.123</td>
                                <td>Binary</td>
                                <td class="fill no-monospace"><button class="btn">View</button></td>
                            </tr>*/

                            let d = whatsAppMessage.data;
                            let viewJSONButton = $("<button></button>").addClass("btn").html("View").click(function() {
                                let messageIndex = parseInt($(this).parent().parent().attr("data-message-index"));
                                let jsonData = allWhatsAppMessages[messageIndex];
                                let tree, collapse = false;
                                let dialog = bootbox.dialog({
                                    title: `WhatsApp message #${messageIndex+1}`,
                                    message: "<p>Loading JSON...</p>",
                                    buttons: {
                                        noclose: {
                                            label: "Collapse/Expand All",
                                            className: "btn-info",
                                            callback: function () {
                                                if (!tree)
                                                    return true;

                                                if (collapse === false)
                                                    tree.expand();
                                                else
                                                    tree.collapse();

                                                collapse = !collapse;

                                                return false;
                                            }
                                        }
                                    }
                                });
                                dialog.init(() => {
                                    tree = jsonTree.create(jsonData, dialog.find(".bootbox-body").empty()[0]);
                                });
                            });

                            // set statuses
                            setStatuses(d);
                            // set contacts
                            setContacts(d);

                            let tableRow = $("<tr></tr>").attr("data-message-index", allWhatsAppMessages.length);
                            tableRow.append($("<th></th>").attr("scope", "row").html(allWhatsAppMessages.length+1));
                            tableRow.append($("<td></td>").html(moment.unix(d.timestamp/1000.0).format("ddd, DD.MM.YYYY, HH:mm:ss.SSS")));
                            tableRow.append($("<td></td>").html(d.message_type));
                            tableRow.append($("<td></td>").addClass("fill no-monospace").append(viewJSONButton));
                            $("#messages-list-table-body").append(tableRow);
                            allWhatsAppMessages.push(d.message);

                            //$("#main-container-content").empty();
                            //jsonTree.create(whatsAppMessage.data.message, $("#main-container-content")[0]);
                        }).run();
                    },
                    timeoutCondition: websocket => websocket.backendConnectedToWhatsApp
                }
            })

        ]
    };
    $("#restore-session").addClass("hidden");

    $("#restore-session").click(function() {
        bootstrapInfo.steps[4].run(apiInfo.timeout).then(() => {
            let text = currStep.texts.success.replace("%1", Math.round(performance.now() - stepStartTime));
            $(this).html(text).attr("disabled", false);
            bootstrapState++;
        })
        .catch(reason => {
            let text = currStep.texts.failure.replace("%1", reason);
            $(this).html(text).attr("disabled", false);
        });
    });
    $("#bootstrap-button").click(function() {
        let currStep = bootstrapInfo.steps[bootstrapState];
        let stepStartTime = performance.now();
        $(this).html(currStep.texts.handling).attr("disabled", "true");
        currStep.run(apiInfo.timeout)
            .then(() => {
                let text = currStep.texts.success.replace("%1", Math.round(performance.now() - stepStartTime));
                $(this).html(text).attr("disabled", false);
                bootstrapState++;
            })
            .catch(reason => {
                let text = currStep.texts.failure.replace("%1", reason);
                $(this).html(text).attr("disabled", false);
            });
    });

    $("#button-disconnect").click(function() {
        if(!apiWebsocket.backendConnectedToWhatsApp)
            return;
        
        $(this).attr("disabled", true).html("Disconnecting...");
        new BootstrapStep({
            websocket: apiWebsocket,
            request: {
                type: "call",
                callArgs: { command: "backend-disconnectWhatsApp" },
                successCondition: obj => obj.type == "resource_disconnected"  &&  obj.resource == "whatsapp"
            }
        }).run(apiInfo.timeout)
        .then(() => {
            apiWebsocket.backendConnectedToWhatsApp = false;
            $(this).html("Disconnected.");
        }).catch(reason => $(this).html(`Disconnecting failed: ${reason}. Click to try again.`).attr("disabled", false));
    });
});
