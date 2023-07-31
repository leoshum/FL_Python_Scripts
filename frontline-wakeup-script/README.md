# Wakeup script
The "Wakeup script" is a Python script that performs a series of HTTP requests based on URLs provided in a JSON file to keep the sites cache hot.
## Wakeup script
Before running the script, make sure you have the following prerequisites installed:
- Python 3.x
- Required Python libraries: 
    - requests
    - json
    - argparse

To install all necessary dependencies run this command:

`pip install -r requirements.txt`
## Compilation to .exe
For script compilation to executable file, first install the *pyinstaller* library and then run *build_script.ps1* powershell script:

`.\build_script.ps1`

At the output you will receive an archive with an executable file and config files.
## Windows Scheduler setup
    `.\setup_scheduler.ps1 -ExeFilePath "C:\Path\To\Your\wakeup.exe" -RunAsUser "DOMAIN\Username"`
## Usage
Execute the script with the following command:

`python wakeup.py <urls_file_name> [--sites <site1> <site2> ...]`
- <urls_file_name>: The path to the JSON file containing the URLs.
- --sites: An optional argument to specify the sites you want to include. You can provide one or more site names separated by spaces.

Examples:
`python wakeup.py urls.json --sites athens training`

`python wakeup.py urls.json`

Alternatively, you can also use the executable file:

`wakeup.exe urls.json --sites athens training`

`wakeup.exe urls.json`

The script will process the URLs from the JSON file and log the responses to a log file named wakeup__\<timestamp>.log, where \<timestamp> is the current date and time in the format YYYY-MM-DD_HH-MM.