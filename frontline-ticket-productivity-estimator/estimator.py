import asyncio
from datetime import datetime, timedelta
import json
from os import environ, path
import re
import pandas as pd
import aiohttp
import pytz
# from github import Github

class Estimator:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.jql = '"Story Points" > 5 AND labels=jira_escalated and project="CW-0575 (Accelify)" and status not in ("waiting for response", open, DevReady, "in progress")'
        self.configuration = None
        self.configure()

    def configure(self, name='configuration.json', update={}):
        if self.configuration is None:
            self.root_directory = path.dirname(__file__)
            self.result_path = f'{self.root_directory}\\result.xlsx'
            with open(f'{self.root_directory}\\{name}', mode = 'r', encoding='utf-8') as configuration_file:
                self.configuration = json.load(configuration_file)

            #Jira
            self.auth = aiohttp.BasicAuth(
                login=self.configuration.get('jira_login'),
                password=environ.get('JIRA_TOKEN'))
            self.jira_url = f'https://{self.configuration.get("jira_host")}/rest/api/2/search'

            #Git
            script_folder = path.normpath(self.root_directory + '\\..\\frontline-ticket-parser')
            self.find_script_path = f"{script_folder}\\find_tickets.ps1"
            self.repository_path = self.configuration.get('repository_path')
            self.git_branch = self.configuration.get('git_branch')
            self.ssh_key_path = self.configuration.get('ssh_key_path')
            self.commit_regex = re.compile(r"^commit\s+(\w+)")
            
            #GitHub
            self.github_url = f'https://api.github.com/repos/{self.configuration.get("github_owner") }/{self.configuration.get("github_repository")}'
            self.github_token = environ.get('GITHUB_TOKEN')

        self.configuration.update(update)

    async def get_jira_issues(self, stored_issues=None):
        if stored_issues:
            numbers = [issue.get('number') for issue in stored_issues]
        else:
            numbers = []

        start_at = 0
        max_results = 50
        headers = {'Accept': 'application/json'}
        date_format = "%Y-%m-%dT%H:%M:%S.%f%z"
        
        total_issues = 1
        end_date = datetime.now(pytz.utc) - timedelta(days=30*4)
        async with aiohttp.ClientSession() as session:
            while start_at < total_issues:# and start_at < 50
                # Set up the API request with the appropriate startAt and maxResults values
                url = f'{self.jira_url}?jql={self.jql}&startAt={start_at}&maxResults={max_results}'

                # Make the API call with the authenticated session
                async with session.get(url, headers=headers, auth=self.auth) as response:
                    if response.status == 200:
                        data = await response.json()
                        if total_issues == 1 and data.get('total') != 1:
                            total_issues = data['total']

                        # result.extend(data['issues'])
                        print(f'Get [{start_at}] - [{start_at + max_results - 1}] issues from Jira.')
                        for issue in data.get('issues'):
                            if issue.get('key') in numbers:
                                if datetime.strptime(issue.get('fields').get('updated'), date_format) < end_date: return
                                continue
                            # if last_number >= re.findall(number_regex, issue.get('key'))[0]: return
                            yield issue                 
                    else:
                        print(f'Request failed with status {response.status}: {response.reason}')
                        return

                # Increment the startAt value to get the next page of results
                start_at += max_results
                
            # with open(result_path, mode='w', encoding='UTF-8') as file:
            #     file.write(json.dumps([issue['fields']['status']['name'] for issue in result], indent=2, ensure_ascii=False))
            # return [{ 'key': issue['key'], 'status' : issue['fields']['status']['name']} for issue in result]

    async def configure_git(self):
        process = await asyncio.create_subprocess_exec(
            'powershell', '-File', self.find_script_path, '-Repository_path', self.repository_path, '-Branch_name', self.git_branch, '-Key_Path', self.ssh_key_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # read the stdout and stderr asynchronously
        stdout, stderr = await process.communicate()
        print(stdout.decode(), stderr.decode())

    async def find_in_git(self, issue):
        process = await asyncio.create_subprocess_exec(
            'powershell', '-File', self.find_script_path, '-Repository_path', self.repository_path, '-Ticket_number', issue['key'],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            print(f'Ticket [{issue["key"]}] not found in Git')
            return None
        
        print(f'Ticket [{issue["key"]}] found in Git')
        return json.loads(stdout.decode('utf-8'))[0]
    
    def parse_commit(self, commit):
        mathces = re.findall(self.commit_regex, commit[0])
        return mathces[0]

    async def get_commit_info(self, commit_sha):
        url = f'{self.github_url}/commits/{commit_sha}'
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            "Authorization": f"token {self.github_token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        commit_data = await response.json()
                        files_changed = len(commit_data['files'])
                        lines_added = sum(file['additions'] for file in commit_data['files'])
                        lines_removed = sum(file['deletions'] for file in commit_data['files'])
                        return files_changed, lines_added, lines_removed
                    else:
                        raise Exception(f"Failed to retrieve commit information. Status code: {response.status}, Response: {response.text}")

    def write_to_excel(self, tickets):
        df = pd.DataFrame(tickets)
        df.to_excel(self.result_path, index=False)

# Example usage
async def main():
    tickets = []
    estimator = Estimator()
    await estimator.configure_git()

    async for issue in estimator.get_jira_issues():
        ticket = {
            "Number": issue.get("key"),
            "Jira URL" : f'https://frontlinetechnologies.atlassian.net/browse/{issue.get("key")}',
            "Sory Points" : issue['fields']['customfield_10021']
        }
        tickets.append(ticket)

        find_result = await estimator.find_in_git(issue)
        if not find_result: continue
        
        commit_sha = estimator.parse_commit(find_result)
        ticket['Commit URL'] = f'https://github.com/FrontlineEducation/CW-0575-IEP/commit/{commit_sha}'

        files_changed, lines_added, lines_removed = await estimator.get_commit_info(commit_sha)
        ticket['Files changed'] = files_changed
        ticket['Lines added'] = lines_added
        ticket['Lines removed'] = lines_removed
    
    estimator.write_to_excel(tickets)
# Run the main function
asyncio.run(main())
