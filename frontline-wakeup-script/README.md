# Wakeup script
The "Wakeup script" is a Python script that performs a series of HTTP requests based on URLs provided in a JSON file to keep the sites cache hot.
## Wakeup script
Before running the script, make sure you have the following prerequisites installed:
- Python 3.x
- Required Python libraries: 
    - requests
    - json
    - argparse
    - beautifulSoup
## Usage
Execute the script with the following command:
`python wakeup.py <urls_file_name> [--sites <site1> <site2> ...]`
- <urls_file_name>: The path to the JSON file containing the URLs.
- --sites: An optional argument to specify the sites you want to include. You can provide one or more site names separated by spaces.

Examples:
`python wakeup.py urls.json --sites athens tx`
`python wakeup.py urls.json`

The script will process the URLs from the JSON file and log the responses to a log file named wakeup__\<timestamp>.log, where \<timestamp> is the current date and time in the format YYYY-MM-DD_HH-MM.