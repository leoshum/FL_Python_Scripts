//const { readFileSync } = require("fs");
// const { exec } = require("child_process");
// const { $ } = require("jquery")
//const cors = require('cors');

const base_url = 'http://localhost:3443'
const prs_path = `${base_url}/prs.json`;

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
        $('<td>').text(files)
    );

    // Create the details row for the current item
    var $detailsRow = $('<tr>', {
        id: 'row' + index,
        class: 'collapse',
        colspan: 3
    }).append(
        $('<td>', { colspan: 5 }).append(
            $('<div>').append(
                $('<h5>').text('Commits:'),
                $('<ul>').append(
                    item.commits.map(function(commit) {
                        return $('<li>', { class : 'commit'}).append(
                            'Name: ',
                            $('<a>', { href: commit.Url }).text(commit.Message),
                            $('<br>'),
                            'Author: ',
                            $('<strong>').append(
                                commit.Author),
                            $('<br>'),
                            'Date: ' + commit['Create Date'],
                            $('<br>'),
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
                                        $('<div>', { class : 'col-md-3 review'}).append(
                                            file.review
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

// var tbody = document.getElementsByTagName('tbody')[0];
// tbody.appendChild($row[0]);
// tbody.appendChild($detailsRow[0]);
fill_table();
// $(document).ready(function() {
//     get_prs().then(data => {
//         var tr;
//         for (var i = 0; i < data.length; i++) {

//             tr = $('<tr/>');
//             tr.append("<td>" + data[i].number + "</td>" );   // Append table row with JSON data items 
//             tr.append("<td>" + data[i]['Merged by'] + "</td>" );   // Append table row with JSON data items
//             tr.append("<td>" + data[i].Url + "</td>" );   // Append table row with JSON data items
//             tr.append("<td>" + data[i].Comments + "</td>" );
//             tr.append("<td>" + data[i].commits + "</td>" );   // Append table row with JSON data items

//             $('#example').append(tr);    // Append all the rows to the table body (tbody) element which is already defined in HTML code
//         }
//     })
// })


// async function get_json(path){
//     try {
//         const response = await fetch(path, {'cache': 'no-cache'})
//         if(response.ok){
//             return await response.json()
//         }
//     }
//     catch(error){
//         console.log(error)
//     }
// }
// get_json(prs_path).then(r => {
//     const json = r; console.log(json)
// })
// provide example for bootstrap table from json file
// function run_analyzer(path){
//     exec(`python ${path}`, (error, stdout, stderr) => {
//         if (error) {
//             console.log(`error: ${error.message}`);
//             return;
//         }
//         if (stderr) {
//             console.log(`stderr: ${stderr}`);
//             return;
//         }
//         console.log(`stdout: ${stdout}`);
//     })
// }

// function get_file(path){
//     try {
//         if (fs.existsSync(path)) {
//             return readFileSync(path,'utf8');
//         }
//         else
//         {
//             run_analyzer(analyzer_path);
//         }
//     } catch(err) {
//         console.log(`Error: ${err}`);
//     }
// }

// const analyzer_path = '..\\analyzer.py';

// let prs_file = get_file(prs_path)
// const jsontext = JSON.parse(prs_file);

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

$('#update').on('click', async e => {
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
})

//add date and commit author