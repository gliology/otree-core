// todo: rename to onPageLoad
ot.onLoad(function () {
    ot.freezeInputs();
    ot.startIteration();
});

ot.onIteration(function () {
    delete ot.page.trial;
    delete ot.page.response;
    delete ot.page.feedback;

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
        console.log('did startIteration', ot.page.progress.completed);
    });
});
