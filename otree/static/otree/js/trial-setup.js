function makeTrialSocket() {
  var $currentScript = $('#otree-trial');
  var socketUrl = $currentScript.data('socketUrl');
  return makeReconnectingWebSocket(socketUrl);
}

window._trialSocket = makeTrialSocket();
