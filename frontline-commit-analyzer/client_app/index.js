const { spawn, exec } = require("child_process");
const express = require('express');
const path = require('path');


const PORT = 3443

const prs_path = `${__dirname}/prs.json`;
const index_path = `${__dirname}/index.html`;
const analyzer_path = path.normalize(`${__dirname}\\..\\analyzer.py`);


const app = express();

app.use(express.static('public'));

app.get('/analyze', async (req, res) => {
    const hours = req.query.hours;

    new Promise((resolve, reject) => {
        const childProcess = spawn('python', [analyzer_path, hours]);
    
        childProcess.stdout.on('data', (data) => {
            console.log(`stdout: ${data}`);
        });
    
        childProcess.stderr.on('data', (data) => {
            console.log(`stderr: ${data}`);
        });
    
        childProcess.on('close', (code) => {
            console.error(`Exit code: ${code}`);
            if (code == 0) {
                res.status(200).send();
            } else {
                res.status(500).send();
            }
            resolve();
        });
    
        childProcess.on('error', (err) => {
            res.status(500).send(`Failed to start child process: ${err}`);
            reject(err);
        });
    });
});

app.get('/prs', (req, res) => {
    res.sendFile(prs_path);
});

app.get('/', (req, res) => {
    res.sendFile(index_path);
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server started on port ${PORT}`);
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

try {
    exec(`"%ProgramFiles(x86)%\\Google\\Chrome\\Application\\chrome.exe" http://localhost:${PORT}`, (error, stdout, stderr) => {
        if (error) {
            console.log(`error: ${error.message}`);
            return;
        }
        if (stderr) {
            console.log(`stderr: ${stderr}`);
            return;
        }
        if (stdout) {
            console.log(`stdout: ${stdout}`);
            return;
        }
    });    
} catch (error) {
    console.log(`Error during open chrome: ${error}`);    
}