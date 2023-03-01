const base_url = 'http://localhost:3443'
const prs_path = `${base_url}/prs.json`;

async function get_prs(){
    const url = `${base_url}/prs.json`;
    try {
        const response = await fetch(url, {'cache': 'no-cache'})
        if(response.ok){
            return await response.json()
        }
    }
    catch(error){
        console.log(error)
    }
}

function fill_table(){
    get_prs().then(data => {
        // Get the tbody element
var tbody = $('tbody');

// Remove all rows from the table
tbody.empty();

// Iterate over each item in the data array
$.each(data, function(index, item) {

    // Count the number of files in all commits for the current item
    var files = item.commits.reduce(function(sum, commit) {
        return sum + commit.Files.length;
    }, 0);
    var ai_warnings = item.commits.reduce(function(sum, commit) {
        return sum + commit.Files.reduce(function(sum, file) {
            if (file.state == 2) {
                return sum;
            }
            return sum + 1;
        }, 0);
    }, 0);

    // Create the main row for the current item
    var $row = $('<tr>', {
        'data-toggle': 'collapse',
        'data-target': '#row' + index,
        'aria-expanded': false,
        'aria-controls': 'row' + index
    }).append(
        $('<td>').append(
            $('<a>', { href: item.Url }).text(item.number)
        ),
        $('<td>').text(item['Merged by']),
        $('<td>').append(
            $('<ul>').append(
                item.Comments.map(function(comment) {
                    return $('<li>').append(
                        $('<strong>').text('[' + comment.State + '] ' + comment.Author + ':'),
                        ' ' + comment.Text
                    );
                })
            )
        ),
        $('<td>').text(item.commits.length),
        $('<td>').text(files),
        $('<td>').text(ai_warnings)
    );

    // Create the details row for the current item
    var $detailsRow = $('<tr>', {
        id: 'row' + index,
        class: 'collapse',
        colspan: 3
    }).append(
        $('<td>', { colspan: 6 }).append(
            $('<div>').append(
                $('<h5>').text('Commits:'),
                $('<ul>').append(
                    item.commits.map(function(commit) {
                        return $('<li>', { class : 'commit'}).append(
                            'Name: ',
                            $('<a>', { href: commit.Url }).text(commit.Message),
                            $('<div>', { class : 'commit-info' }).append(
                                'Author: ',
                                $('<strong>').append(
                                    commit.Author),
                                $('<br>'),
                                'Creation date: ' + commit['Create Date'],
                                $('<br>'),
                                'Upload date: ' + commit['Upload Date'],),
                            $('<div>', { class: 'row' }).append(
                                $('<div>', { class: 'col-md-8 tab-name' }).append(
                                    $('<strong>').append(
                                        'Files' )),
                                $('<div>', { class : 'col-md-3 tab-name'}).append(
                                    $('<strong>').append(
                                        'AI Review' )),
                                $('<div>', { class : 'col-md-1 tab-name'}).append(
                                    $('<strong>').append(
                                        'AI Status' ))),
                            $('<ul>').append(
                                commit.Files.filter(function(file) {
                                    return file.patch;
                                }).map(function(file) {
                                    var patchHeaderRegex = /^@@\s-(\d+),(\d+)\s\+(\d+),(\d+)\s@@/;
                                    var patchHeader = file.patch.match(patchHeaderRegex);
                                    var patchLines = file.patch.split('\n');

                                    return $('<li>', { class: 'row' }).append(
                                        $('<div>', { class: 'col-md-8 file code' }).append(
                                            $('<strong>').text(file.name + ':'),
                                            $('<div>', { class: 'diff' }).append(
                                                patchLines.map(function(line) {
                                                    var classAttribute = '';
                                                    if (line.startsWith('+')) {
                                                        classAttribute = 'diff-added';
                                                    } else if (line.startsWith('-')) {
                                                        classAttribute = 'diff-removed';
                                                    }
                                                    return $('<div>', { class: classAttribute }).text(line.trim());
                                                })
                                            )
                                        ),
                                        $('<div>', { class : 'col-md-3 review-container'}).append(
                                            $('<div>', { class : 'review'}).append(
                                                file.review
                                            )
                                        ),
                                        $('<div>', { class : 'col-md-1 review-status-container'}).append(
                                            $('<div>', { class : 'review-status'}).append(function() {
                                                var iconClass;
                                                switch (file.state) {
                                                    case 0:
                                                        iconClass = 'bi-x-circle-fill bad-state-icon'; // Bad icon
                                                        break;
                                                    case 1:
                                                        iconClass = 'bi-exclamation-triangle-fill warning-state-icon'; // Warning icon
                                                        break;
                                                    case 2:
                                                        iconClass = 'bi-check-circle-fill good-state-icon'; // Good icon
                                                        break;
                                                }
                                                return $('<span>', { class: 'bi ' + iconClass });
                                            }),
                                            $('<button>', { class: 'btn btn-primary refresh-review', sha: file.sha }).append(
                                                $('<i>', { class: 'bi bi-arrow-clockwise' })                                        
                                            ).on('click', async (e) => {
                                                let button = $(e.currentTarget);
                                                button.prop('disabled', true);
                                                var sha = button.attr('sha');
                                                
                                                const url = `${base_url}/review?sha=${sha}`;
                                                try {
                                                    const response = await fetch(url, {'cache': 'no-cache'})
                                                    if(response.ok){
                                                        button.parent().parent().find('.review').text(await response.text());
                                                    }
                                                }
                                                catch(error){
                                                    console.log(error)
                                                }
                                                finally {
                                                    button.prop('disabled', false);
                                                }
                                            })
                                        )
                                    );
                                })
                            )
                        );
                    })
                )
            )
        )
    );

    // Add the main and details rows to the table
            var tbody = document.getElementsByTagName('tbody')[0];
            tbody.appendChild($row[0]);
            tbody.appendChild($detailsRow[0]);
});

// Attach the collapse toggle to the main rows
tbody.on('click', 'tr[data-toggle="collapse"]', function() {
    var target = $(this).data('target');
    $(target).collapse('toggle');
});

        
    })
}

fill_table();

let update = $('#update')
update.on('click', async e => {
    update.prop('disabled', true);
    const hours = $('#hours').val();
    const url = `${base_url}/analyze?hours=${hours}`;
    try {
        const response = await fetch(url, {'cache': 'no-cache'})
        if(response.ok){
            fill_table();
        }
        console.log(await response.text()) 
    }
    catch(error){
        console.log(error)
    }
    finally {
        update.prop('disabled', false);
    }
})