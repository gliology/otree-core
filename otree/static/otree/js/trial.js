var _trialSocket;

function makeTrialSocket() {
  var $currentScript = $('#otree-trial');
  var socketUrl = $currentScript.data('socketUrl');
  return makeReconnectingWebSocket(socketUrl);
}

_trialSocket = makeTrialSocket();


// prevent form submission when user presses enter in an input
$(document).ready(function() {
  $('input').on('keypress', function (e) {
      if (e.key === 'Enter') {
          e.preventDefault();
      }
  });
});
