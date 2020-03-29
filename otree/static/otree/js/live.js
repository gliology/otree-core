var liveSocket;

var $currentScript = $('#otree-live');

var socketUrl = $currentScript.data('socketUrl');

liveSocket = makeReconnectingWebSocket(socketUrl);

liveSocket.onmessage = function (e) {
    var data = JSON.parse(e.data);

    if (liveRecv !== undefined) {
        liveRecv(data);
    }
};

function liveSend(msg) {
    liveSocket.send(JSON.stringify(msg));
}
