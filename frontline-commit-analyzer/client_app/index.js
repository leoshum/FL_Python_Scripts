const { exec } = require("child_process");
const express = require('express');

const app = express();

const prs_path = `${__dirname}/prs.json`;
const index_path = `${__dirname}/index.html`;
const analyzer_path = `${__dirname}/../analyzer.py`;
const logic_path = `${__dirname}/logic.js`;

app.get('/analyze', (req, res) => {
    exec(`python ${analyzer_path}`, (error, stdout, stderr) => {
        if (error) {
            console.log(`error: ${error.message}`);
            res.send('Bad');
            return;
        }
        if (stderr) {
            console.log(`stderr: ${stderr}`);
            res.send('Bad');
            return;
        }
        console.log(`stdout: ${stdout}`);
    })

    res.send('Ok');
});

app.get('/prs', (req, res) => {
    res.sendFile(prs_path);
});

app.get('/', (req, res) => {
    res.sendFile(index_path);
});
app.get('/logic.js', function(req, res) {
    res.setHeader('Content-Type', 'text/javascript');
    res.sendFile(logic_path);
});

// Start the server
app.listen(3000, () => {
    console.log('Server started on port 3000');
});

// var http = require('http');
// var fs = require('fs');

// const PORT=8080; 

// fs.readFile('./index.html', function (err, html) {

//     if (err) throw err;    

//     http.createServer(function(request, response) {  
//         response.writeHeader(200, {"Content-Type": "text/html"});  
//         response.write(html);  
//         response.end();  
//     }).listen(PORT);
// });


// exec(`"%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe" ${__dirname}\\index.html`, (error, stdout, stderr) => {
//     if (error) {
//         console.log(`error: ${error.message}`);
//         return;
//     }
//     if (stderr) {
//         console.log(`stderr: ${stderr}`);
//         return;
//     }
//     if (stdout) {
//         console.log(`stdout: ${stdout}`);
//         return;
//     }
// });