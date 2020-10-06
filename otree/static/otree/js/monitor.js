function initWebSocket(socketUrl, $tbody, visitedParticipants) {
    monitorSocket = makeReconnectingWebSocket(socketUrl);
    monitorSocket.onmessage = function (e) {
        var data = JSON.parse(e.data);
        if (data.type === 'update_notes') {
            updateNotes($tbody[0], data.ids, data.note);
        }
        else {
            refreshTable(data.rows, $tbody, visitedParticipants);
        }
    }
}

// ajax request for advance session button
function setup_ajax_advance(ajaxUrl) {
    var csrftoken = $("[name=csrfmiddlewaretoken]").val();

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    $('#advance_users').on('click', function () {
        $('#advance_users').attr("disabled", true);
        $.ajax({
            url: ajaxUrl,
            type: 'POST',
            error: function (jqXHR, textStatus) {
                $("#auto_advance_server_error").show();
                // enable the button so they can try again?
                $('#advance_users').attr("disabled", false);
            },
            success: function () {
                $("div#auto_advance_server_error").hide();
                $('#advance_users').attr("disabled", false);
            }
        });
    });
}

function getNthBodyRowSelector(n) {
    return `tr:nth-of-type(${n+1})`;
    //return `tr:eq(${n})`;
}

function updateNotes(tbody, ids, note) {
    for (let id of ids) {
        let index = visitedParticipants.indexOf(id);
        if (index >= 0) {
            updateNthRow(tbody, index, {_monitor_note: note});
        }
    }
}

function updateNthRow(tbody, n, row) {
    let nthBodyRow = tbody.querySelector(getNthBodyRowSelector(n));
    for (let fieldName of Object.keys(row)) {
        let cellToUpdate = nthBodyRow.querySelector(`td[data-field='${fieldName}']`);
        if (cellToUpdate == null) {
            console.log(n);
        }
        let prev = cellToUpdate.dataset.value;
        let cur = row[fieldName];
        let dataSetVal = makeCellDatasetValue(cur);
        if (prev !== dataSetVal) {
            cellToUpdate.dataset.value = dataSetVal;
            cellToUpdate.innerHTML = makeCellDisplayValue(fieldName, cur);
            flashGreen($(cellToUpdate));
        }
    }
}

function refreshTable(new_json, $tbody, visitedParticipants) {

    let tbody = $tbody[0];
    let hasNewParticipant = false;
    for (let fullRow of new_json) {
        const {id_in_session, ...row} = fullRow;
        let index = visitedParticipants.indexOf(id_in_session);
        if (index === -1) {
            index = visitedParticipants.filter((id) => id < id_in_session).length;
            let newRow = createTableRow(row);
            let rowSelector = getNthBodyRowSelector(index);
            if (index === visitedParticipants.length) {
                tbody.appendChild(newRow);
            } else {
                tbody.insertBefore(newRow, tbody.querySelector(index));
            }
            let tr = tbody.querySelector(rowSelector);
            flashGreen($(tr));
            visitedParticipants.splice(index, 0, id_in_session);
            hasNewParticipant = true;
        } else {
            updateNthRow(tbody, index, row);
        }
    }
    if (hasNewParticipant) {
        $('#num_participants_visited').text(visitedParticipants.length);
    }
    $(".timeago").timeago();
}