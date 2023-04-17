// todo: rename to onPageLoad
ot.onLoad(function () {
    ot.freezeInputs();
    ot.startIteration();
});

ot.onIteration(function () {
    delete ot.page.trial;
    delete ot.page.feedback;
    // should we automatically delete response? doesn't seem good
    // to special-case this variable name.
    delete ot.page.response;


    let nextTrial = ot.getPlayableTrial();
    if (nextTrial) {
        ot.startTrial(nextTrial);
    } else {
        ot.completePage();
    }
});

ot.onTrial(function (trial) {
    ot.page.trial = trial;
    ot.resetInputs();
});

// don't pass feedback to onCompleteTrial.
// the user should set ot.page.feedback in onInput or somewhere else.
// this makes it easier to handle both half-live and full-live mode.
ot.onComplete(function () {
    ot.delay(window.TRIAL_DELAY || 0, function () {
        ot.startIteration();
    });
});
