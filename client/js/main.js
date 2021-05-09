let consoleShown = false;
let apiWebsocket = new WebSocketClient();

function sleep(ms) {
    return new Promise((resolve, reject) => {
        setTimeout(() => resolve(), ms);
    });
}
function request_chat_history(jid) {
    new BootstrapStep({
        websocket: apiWebsocket,
        request: {
            type: "call",
            callArgs: { command: "backend-getChatHistory", jid: jid },
            successCondition: obj => "jid" in obj && "type" in obj &&
                obj.jid === jid && obj.type === "chat_history" && "messages" in obj && Array.isArray(obj.messages),
            successActor: (websocket, {messages, jid})=>  {
                download("messages-" + jid + ".json", JSON.stringify(messages));
            }
        }
    }).run().catch(() => currentRequestJID = null);
}
/**
 * https://stackoverflow.com/questions/3665115/how-to-create-a-file-in-memory-for-user-to-download-but-not-through-server
 * @param filename
 * @param text
 */
function download(filename, text) {
    var element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    element.setAttribute('download', filename);

    element.style.display = 'none';
    document.body.appendChild(element);

    element.click();

    document.body.removeChild(element);
}

$(document).ready(function() {
    $("#formDlChat").submit((event) => {
        event.preventDefault();
        request_chat_history($("#chatDlRemoteJID").val());
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
        deactivated: false,
        activateButton: (text, buttonEnabled) => {
            let container = $("#bootstrap-container").removeClass("hidden").children("#bootstrap-container-content");
            container.children("img").detach();
            container.children("button").removeClass("hidden").html(text).attr("disabled", !buttonEnabled);
            $("#main-container").addClass("hidden");

            $("#formDlChat").addClass("hidden");
            this.deactivated = false;

            allWhatsAppMessages = [];
            $("#messages-list-table-body").empty();
        },
        activateQRCode: image => {
            let container = $("#bootstrap-container").removeClass("hidden").children("#bootstrap-container-content");
            container.children("button").addClass("hidden")
            container.append($("<img>").attr("src", image));
            $("#main-container").addClass("hidden");
        },
        deactivate: () => {
            if (this.deactivated) return;
            this.deactivated = true;
            $("#bootstrap-container").addClass("hidden")

            $("#formDlChat").removeClass("hidden");
            $("#main-container").removeClass("hidden");
            $("#button-disconnect").html("Disconnect").attr("disabled", false);

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
                    websocket.waitForMessage({
                        condition: obj => obj.type == "resource_gone"  &&  obj.resource == "whatsapp",
                        keepWhenHit: false
                    }).then(() => {
                        bootstrapInfo.activateButton(bootstrapInfo.steps[2].texts.connLost, true);
                        bootstrapState = 2;
                        websocket.backendConnectedToWhatsApp = false;
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
