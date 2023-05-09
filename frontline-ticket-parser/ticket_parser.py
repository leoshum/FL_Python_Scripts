import datetime
import json
from os import environ, path
import re
import subprocess
import aiohttp
import asyncio

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import pandas as pd


branch_name = 'main'
repository_path = 'C:\\Users\\mykha\\source\\repos\\CW-0575-IEP'
token_name = 'JIRA_TOKEN'
jira_token = environ.get(token_name)
#JIRA query: you can try this search in zendesk - jira_escalated brand:plan status:new status:hold status:open status:pending (edited) 


token_name = 'TEAM_CITY_TOKEN'
teamcity_token = environ.get(token_name)
if teamcity_token is None:
    print(f"TeamCity bearer token not found in environments variable with name [{token_name}]!")
    exit()

#Service
jira_url = 'https://frontlinetechnologies.atlassian.net/rest/api/2/search'
teamcity_url = 'https://teams.acceliplan.com'
root_directory = path.dirname(__file__)
find_script_path = f"{root_directory}\\find_tickets.ps1"
switch_script_path = f"{root_directory}\\switch_and_update_branch.ps1"
result_path = f"{root_directory}\\result.json"

async def get_tickets_from_jira(session):
    # Authenticate with Jira
    auth = aiohttp.BasicAuth(login='mtolstikhin@frontlineed.com', password=jira_token)
    # Set up the API request
    
    # exclude
    # waiting for response
    # open
    # devready
    # in progress
    
    jql_query = 'labels=jira_escalated and project="CW-0575 (Accelify)"'
    start_at = 0
    max_results = 50
    headers = {'Accept': 'application/json'}


    result = []
    # Make the initial API call to get the total number of issues
    url = f'{jira_url}?jql={jql_query}&startAt={start_at}&maxResults={max_results}'
    async with session.get(url, headers=headers, auth=auth) as response:
        if response.status == 200:
            data = await response.json()
            total_issues = data['total']
            result.extend(data['issues'])
            print(f'Get [{start_at}] - [{start_at + max_results - 1}] issues.')
            start_at += max_results
        else:
            print(f'Request failed with status {response.status}: {response.reason}')
            return

    # Loop through the paginated API responses
    while start_at < total_issues and start_at < 50:
        # Set up the API request with the appropriate startAt and maxResults values
        url = f'{jira_url}?jql={jql_query}&startAt={start_at}&maxResults={max_results}'

        # Make the API call with the authenticated session
        async with session.get(url, headers=headers, auth=auth) as response:
            if response.status == 200:
                data = await response.json()
                result.extend(data['issues'])
                print(f'Get [{start_at}] - [{start_at + max_results - 1}] issues.')
            else:
                print(f'Request failed with status {response.status}: {response.reason}')
                return

        # Increment the startAt value to get the next page of results
        start_at += max_results
    return [issue['key'] for issue in result]

def find_in_git(ticket_numbers):
    tickets = []
    not_founded = []
    result = subprocess.run(['powershell', '-File', switch_script_path, '-Repository_path', repository_path, '-Branch_name', branch_name])
    if result.returncode != 0:
        output = json.loads(result.stdout.decode('utf-8'))
        raise f'Can not switch branch [{output}]'


    for ticket_number in ticket_numbers:
        result = subprocess.run(['powershell', '-File', find_script_path, '-Repository_path', repository_path, '-Ticket_number', ticket_number], capture_output=True)
        if result.returncode != 0:
            not_founded.append({                
                'number' : ticket_number
            })
            print(f'Ticket [{ticket_number}] not founded')
        else:
            output = json.loads(result.stdout.decode('utf-8'))
            tickets.append({
                'number' : ticket_number,
                'commits' : output
            })
            print(f'Ticket [{ticket_number}] founded')
    return tickets

def parse_tickets(tickets):
    commit_regex = re.compile(r"^commit\s+(\w+)") #'^commit [0-9a-f]{40}$'
    author_regex = re.compile(r"^Author:\s+(.*)\s+<.*>")
    email_regex = re.compile(r"^Author:\s+.*\s+<(.*)>")
    date_regex = re.compile(r"^Date:\s+(.*)")
    for ticket in tickets:
        for index, commit in enumerate(ticket.get('commits')):
            parsed_commit = {
                'sha' : None,
                'author' : None,
                'email' : None,
                'date' : None,
                'description' : []
            }
            for line in commit:
                if parse_line(parsed_commit, 'sha', line, commit_regex): continue
                if parse_line(parsed_commit, 'author', line, author_regex) and parse_line(parsed_commit, 'email', line, email_regex): continue
                if parse_line(parsed_commit, 'date', line, date_regex):
                    parsed_commit['date'] = datetime.datetime.strptime(parsed_commit.get('date'), "%a %b %d %H:%M:%S %Y %z").isoformat(sep=' ', timespec='seconds')
                    continue
                parsed_commit['description'].append(line)
            parsed_commit['description'] = '\r\n'.join(parsed_commit.get('description'))
            ticket['commits'][index] = parsed_commit

    # for ticket in tickets:
    #     for commit in ticket.get('commits'):
    #         parsed_commit = {
    #             'sha' : None,
    #             'author' : None,
    #             'email' : None,
    #             'date' : None,
    #             'description' : []
    #         }
    #         for line in commit:
    #             if parse_line(parsed_commit, 'sha', line, commit_regex): continue
    #             if parse_line(parsed_commit, 'author', line, author_regex) and parse_line(parsed_commit, 'email', line, email_regex): continue
    #             if parse_line(parsed_commit, 'date', line, date_regex):
    #                 parsed_commit['date'] = datetime.datetime.strptime(parsed_commit.get('date'), "%a %b %d %H:%M:%S %Y %z")
    #                 continue
    #             parsed_commit.get('description').append(line)
    #         parsed_commit['description'] = '\r'.join(parsed_commit.get('description'))
    #         ticket.get('commits')[ticket.get('commits').index(commit)] = parsed_commit


                # if not parsed_commit.get('sha'):
                #     commit_sha = re.findall(commit_regex, line)
                #     if len(commit_sha) != 0:
                #         parsed_commit['sha'] = commit_sha[0]
                #         continue
                # if 

                # author_and_email = re.findall(author_regex, line)[0]
                # author = author_and_email[0]
                # email = author_and_email[1]

                # date_string = re.findall(date_regex, line)[0]
                # date = datetime.datetime.strptime(date_string, "%a %b %d %H:%M:%S %Y %z")

                # print('')

def parse_line(commit, key, line, regex):
    if not commit.get(key):
        mathces = re.findall(regex, line)
        if len(mathces) != 0:
            commit[key] = mathces[0]
            return True
    return False
            


async def find_build(session, tickets):
    headers = {
        'Accept': 'application/json',
        'Authorization' : f'Bearer {teamcity_token}'
    }

    for ticket in tickets:
        for commit in ticket.get('commits'):
            sha = commit.get('sha')
            url = f'{teamcity_url}/app/rest/builds?locator=revision:{sha}'
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    builds = data.get('build')
                    if builds:
                        commit['build'] = []
                        for build in builds:
                            commit['build'].append(build.get('number'))
                    else:
                        commit['build'] = None
                else:
                    print(f'Request failed with status {response.status}: {response.reason}')

import pandas as pd
from openpyxl import load_workbook
def write_to_excel(tickets):

    # Load Excel file

    # Load Excel file
    # filename = 'output.xlsx'
    # book = load_workbook(filename)

    # # Load sheet
    # sheet_name = 'Sheet1'
    # df = pd.read_excel(filename, sheet_name)

    # # Write DataFrame to sheet
    # with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    #     writer.book = book
    #     writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    #     df.to_excel(writer, sheet_name=sheet_name, index=False)

    #     # Adjust column width and row height based on content
    #     for column in writer.sheets[sheet_name].columns:
    #         max_length = 0
    #         column_name = column[0].column_letter  # Get the column name
    #         for cell in column:
    #             try:
    #                 if len(str(cell.value)) > max_length:
    #                     max_length = len(str(cell.value))
    #             except:
    #                 pass
    #         adjusted_width = (max_length + 2) * 1.2
    #         writer.sheets[sheet_name].column_dimensions[column_name].width = adjusted_width
            
    #     for row in writer.sheets[sheet_name].rows:
    #         max_height = 0
    #         for cell in row:
    #             try:
    #                 cell_value = str(cell.value)
    #                 line_count = cell_value.count('\n') + 1
    #                 if line_count > max_height:
    #                     max_height = line_count
    #             except:
    #                 pass
    #         adjusted_height = max_height * 15
    #         writer.sheets[sheet_name].row_dimensions[row[0].row].height = adjusted_height


    df = pd.json_normalize(tickets, record_path=['commits'], meta=['number'])
    df.to_excel('output.xlsx', index=False)
    

async def main():
    async with aiohttp.ClientSession() as session:
        tickets = await get_tickets_from_jira(session)
        print(f'Founded [{len(tickets)}] tickets in Jira')
        result = find_in_git(tickets)
        parse_tickets(result)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False),trust_env=True) as session: #verify_
        
        await find_build(session, result)
        write_to_excel(result)
        with open(result_path, mode='w', encoding='UTF-8') as file:
            file.write(json.dumps(result, indent=2, ensure_ascii=False))


# Run the script
asyncio.run(main())
