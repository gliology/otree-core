/*
Lame trick...I increment the filename when I release a new version of this file,
because on runserver, Chrome caches it, so all oTree users developing on Chrome
would need to Ctrl+F5.
 */

function populateTableBody($tbody, rows) {
    tbody = $tbody[0];
    for (let row of rows) {
        tbody.appendChild(createTableRow(row));
    }
}

function makeCellDatasetValue(value) {
    if (value === null) return '';
    return value.toString();
}

function makeCellDisplayValue(field, value) {
    if (value === null) {
        return '';
    }
    if (field === '_last_page_timestamp') {
        let date = new Date(parseFloat(value) * 1000);
        let dateString = date.toISOString();
        return `<time class="timeago" datetime="${dateString}"></time>`;
    }
    return value;
}

function createTableRow(row) {
    let tr = document.createElement('tr');
    for (let [field, value] of Object.entries(row)) {
        let td = document.createElement('td');
        td.dataset.field = field;
        td.dataset.value = makeCellDatasetValue(value);
        td.innerHTML = makeCellDisplayValue(field, value);
        tr.appendChild(td)
    }
    return tr;
}

function updateDraggable($table) {
    $table.toggleClass(
        'draggable',
        ($table.get(0).scrollWidth > $table.parent().width())
        || ($table.find('tbody').height() >= 450));
}

function flashGreen($ele) {
    $ele.css('background-color', 'green');
    $ele.animate({
            backgroundColor: "white"
        },
        5000
    );
}

let diffpatcher = jsondiffpatch.create({
    objectHash: (obj) => obj.numeric_label
});

function updateTable($table, new_json) {
    let old_json = $table.data("raw");
    let $tbody = $table.find('tbody');
    // build table for the first time
    if (old_json === undefined) {
        populateTableBody($tbody, new_json);
    } else {
        let deltas = diffpatcher.diff(old_json, new_json);
        if (deltas) {
            for (let i of Object.keys(deltas)) {
                // 2017-08-13: when i have time, i should update this
                // to the refactor I did in SessionMonitor.html
                let $row = $tbody.find(`tr:eq(${i})`);
                for (let header_name of Object.keys(deltas[i])) {
                    let cell_to_update = $row.find(`td[data-field='${header_name}']`);
                    let new_value = deltas[i][header_name][1];
                    cell_to_update.text(new_value);
                    flashGreen(cell_to_update);
                }
            }
        }
    }
    $table.data("raw", new_json);
    updateDraggable($table);
}


function makeTableDraggable($table) {
    var mouseX, mouseY;
    $table.mousedown(function (e) {
        e.preventDefault();
        $table.addClass('grabbing');
        mouseX = e.pageX;
        mouseY = e.pageY;
    }).on('scroll', function () {
        $table.find('> thead, > tbody').width($table.width() + $table.scrollLeft());
    });
    $(document)
        .mousemove(function (e) {
            if (!$table.hasClass('grabbing')) {
                return;
            }
            e.preventDefault();
            $table.scrollLeft($table.scrollLeft() - (e.pageX - mouseX));
            var $tableBody = $table.find('tbody');
            $tableBody.scrollTop($tableBody.scrollTop() - (e.pageY - mouseY));
            mouseX = e.pageX;
            mouseY = e.pageY;
        }).mouseup(function (e) {
        if (!$table.hasClass('grabbing')) {
            return;
        }
        e.preventDefault();
        $table.removeClass('grabbing');
    });
}
