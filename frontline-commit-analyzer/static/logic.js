const base_url = 'http://localhost:3443'
const prs_path = `prs.json`;
const file_path = `/file?sha=`;

async function get_json(url){
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

async function get_prs(){
    const url = prs_path;
    return await get_json(url)
}

async function get_file(sha){
    const url = file_path + sha;
    return await get_json(url)
}

function icon(file){
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
}

var warning_element = $('#warnings_count');
var icon_element = $('#icon');
var filtering = "hidden";

warning_element.on('click', function(){
    icon_element.toggleClass('fa-eye-slash');
    if (warning_element.hasClass(filtering)) {
        warning_element.removeClass(filtering);
        fill_table();
        return;
    }
    
    warning_element.addClass(filtering);
    fill_table(true);
})

function fill_table(filtering = false){
    get_prs().then(data => {
        // Get the tbody element
    var tbody = $('tbody');

    // Remove all rows from the table
    tbody.empty();

    if (filtering) {
        // data.filter(function(pr) {
        //     let r = pr.commits.some(function (commit) {
        //         let r = commit.Files.some(function (file) {
        //             let r = file.state === 0 || file.state === 1;
        //             return r;
        //         });
        //         return r;
        //     }
        //     );
        //     return r;
        // });
        data = data.filter(pr => pr.commits.some(commit => commit.Files.some(file => file.state === 0 || file.state === 1)));

        // if (sorting === descending) {
        //     data.sort(function(a, b) {
        //         return b.commits.reduce((sum, commit) => sum + commit.Files.filter(file => file.state <= 1).length) -
        //             a.commits.reduce((sum, commit) => sum + commit.Files.filter(file => file.state <= 1).length);
        //     });
        // }

    }

// Iterate over each item in the data array
$.each(data, function(index, item) {

    // Count the number of files in all commits for the current item
    var files = item.commits.reduce(function(sum, commit) {
        return sum + commit.Files.length;
    }, 0);
    if (files == 0) {
        return;
    }
    var ai_warnings = item.commits.reduce(function(sum, commit) {
        return sum + commit.Files.reduce(function(sum, file) {
            if (file.state === 2 || file.state === "") {
                return sum;
            }
            return sum + 1;
        }, 0);
    }, 0);
    const date = new Date(item['Merged at'])
    const options = {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false
    };
    const formattedDate = date.toLocaleString("en-US", options).replace(/\//g, ".");

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
        $('<td>').text(formattedDate),
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
        $('<td>').text([...new Set(item.commits.map(item => item.Author))].join(', ')),
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
        $('<td>', { colspan: 7 }).append(
            $('<div>').append(
                $('<h5>').text('Commits:'),
                $('<ul>').append(
                    item.commits.map(function(commit) {
                        const createDate = new Date(commit['Create Date']);
                        const uploadDate = new Date(commit['Upload Date']);
                        const formattedUploadDate = uploadDate.toLocaleString("en-US", options).replace(/\//g, ".");
                        const formattedCreateDate = createDate.toLocaleString("en-US", options).replace(/\//g, ".");

                        return $('<li>', { class : 'commit'}).append(
                            'Name: ',
                            $('<a>', { href: commit.Url }).text(commit.Message),
                            $('<div>', { class : 'commit-info' }).append(
                                'Author: ',
                                $('<strong>').append(
                                    commit.Author),
                                $('<br>'),
                                'Creation date: ' + formattedCreateDate,
                                $('<br>'),
                                'Upload date: ' + formattedUploadDate,),
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
                                commit.Files.map(function(file) {
                                    if (file.patch == null || file.patch == '') {
                                        return;
                                        //file.patch = 'Not load'
                                    }
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
                                                return icon(file)
                                            }),
                                            $('<button>', { class: 'btn btn-primary refresh-review', sha: file.sha }).append(
                                                $('<i>', { class: 'bi bi-arrow-clockwise' })                                        
                                            ).on('click', async (e) => {
                                                let button = $(e.currentTarget);
                                                button.prop('disabled', true);
                                                var sha = button.attr('sha');
                                                
                                                const url = `/review?sha=${sha}`;
                                                try {
                                                    const response = await fetch(url, {'cache': 'no-cache'})
                                                    if(response.ok){
                                                        let file = await get_file(sha)
                                                        if (!file){
                                                            throw "Can't find file with sha" + sha
                                                        }
                                                        let parent = button.parent().parent();
                                                        parent.find('.review').text(file.review);
                                                        let status = parent.find('.review-status');
                                                        status.children().remove();
                                                        status.append(icon(file));
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
    const url = `/analyze?hours=${hours}`;
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