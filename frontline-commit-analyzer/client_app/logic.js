//const { readFileSync } = require("fs");
// const { exec } = require("child_process");
// const { $ } = require("jquery")
//const cors = require('cors');

const base_url = 'http://localhost:3000'
const prs_path = `${base_url}/prs.json`;

get_prs().then(data => {
    $.each(data, function(index, item) {
        var $row = $('<tr data-toggle="collapse" data-target="#row' + index + '" aria-expanded="false" aria-controls="row' + index + '">' +
        '<td> <a href="' + item.Url + '">' + item.number + '</a></td>' + '<td>' + item['Merged by'] + '</td>' + '<td>' + item.Comments.length + '</td>' + '<td>' + item.commits.length + '</td>' + '</tr>');
        
        var $detailsRow = $('<tr id="row' + index + '" class="collapse" colspan="3">' + '<td colspan="4">' + '<div class="row">' + '<div class="col-md-3">' +  '<h4>Comments:</h4>' + '<ul>' + $.map(item.Comments, function(comment) {
            return '<li><strong>[' + comment.State + ']' + comment.Author + ':</strong>' + comment.Text + '</li>';
        }).join('') + '</ul>' + '</div>' + '<div class="col-md-9">' + '<h4>Commits:</h4>' + '<ul>' + $.map(item.commits, function(commit) {
            return '<li><strong><a href="' + commit.Url + '">' + commit.sha + '</a>:</strong> ' +'<ul>' + $.map(commit.Files, function(files) {
                return '<li><strong>'+ files.sha + ':</strong> ' + files.patch.replace('\r\n', '<br>').replace('\n', '<br>') + '</li>';
            }).join('')+ '</ul>' + '</li>';
        }).join('') + '</ul>' + '</div>' + '</div>' + '</td>' + '</tr>');
    
        $('tbody').append($row).append($detailsRow);
        jQuery(function($) {
            $('tr[data-toggle="collapse"]').click(function() {
                var target = $(this).data('target');
                $(target).collapse('toggle');
            });
        });
    });
})

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
    const url = `${base_url}/prs`;
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
    const url = `${base_url}/analyze`;
    try {
        const response = await fetch(url, {'cache': 'no-cache'})
        if(response.ok){
            return await response.json()
        }
    }
    catch(error){
        console.log(error)
    }
})