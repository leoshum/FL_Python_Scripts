import asyncio
import json
import logging
import os
import pytz
from datetime import datetime, timedelta
from codeReview import CodeReviewProvider

import aiohttp

class Analyzer:
    def __init__(self):
        file_name = os.path.splitext(os.path.basename(__file__))[0]
        self.root_directory = os.path.dirname(__file__)
        self.pull_request_path = f'{self.root_directory}\\static\\prs.json'
        if os.path.exists(self.pull_request_path):
            self.read_pull_requests()
            self.sha_exist_files = [file['sha'] for pr in self.pull_requests for commit in pr['commits'] for file in commit['Files']]
        else:
            self.pull_requests = []
            self.sha_exist_files = []

        self.logger = logging.getLogger(file_name)
        logging.basicConfig(level=logging.INFO)

        self.time_zone = pytz.utc
        self.utc_now = datetime.now(self.time_zone)
        self.input_format = '%Y-%m-%dT%H:%M:%SZ'

        github_url = 'https://api.github.com'
        repo = 'CW-0575-IEP'
        owner = 'FrontlineEducation'
        self.base_url = f"{github_url}/repos/{owner}/{repo}"
        self.branch = 'develop'
        self.token = os.environ.get('GITHUB_TOKEN')

        self.codereview_provider = CodeReviewProvider(chat_completion=True)

    def read_pull_requests(self):
        with open(self.pull_request_path, mode='r', encoding='UTF-8') as file:
            self.pull_requests = json.load(file)
            
    def write_pull_requests(self):
        self.pull_requests.sort(key=lambda pr: datetime.strptime(pr['Merged at'], self.input_format),reverse=True)
        with open(self.pull_request_path,'w',encoding='UTF-8') as file:
            file.write(json.dumps(self.pull_requests, indent=2, ensure_ascii=False))

    def find_file(self, sha):
        for pull_request in self.pull_requests:
                for commit in pull_request['commits']:
                    for file in commit['Files']:
                        if file['sha'] == sha:
                            return file
                        
        raise Exception(f'Not found commit with sha [{sha}].')

    async def review_commit(self, sha):
        try:
            await self.review_file(self.find_file(sha))
            self.write_pull_requests()
            
            return                            
        except Exception as ex:
            raise Exception(f'Error during update file {ex}.')
    
    async def review_file(self, file):    
        review = ""
        binary_answer = 1
        try:
            url = file.get('filename')

            loop = asyncio.get_event_loop()
            review = await loop.run_in_executor(None, self.codereview_provider.get_code_review, file.get('patch'), url)
            if review == "" or "Skipped" in review or review == None:
                return False
            review = await loop.run_in_executor(None, self.codereview_provider.get_chat_completion_answer, file.get('patch'), url)
            binary_answer = await loop.run_in_executor(None, self.codereview_provider.get_binary_answer, file.get('patch'), url)
            
            binary_answer = "True" in binary_answer or "Skipped" in binary_answer
            if binary_answer:
                binary_answer = 0
            else:
                binary_answer = 2
            
            file['review'] = review
            file['state'] = binary_answer
            self.logger.info(msg=f"Reviewed [{file['sha']}] file.")
            return True
        except Exception as e:
            self.logger.info(msg=f"Review error {e}")
            return False

    async def analyze_commits(self, hours = 12):
        start = self.utc_now - timedelta(hours=hours)
        
        await self.process_commits(start)
    
    async def process_commits(self, start):
        async with aiohttp.ClientSession() as session:
            # Collect commit information
            page = 1
            is_continue = True
            tasks = []
            while is_continue:
                url = f"{self.base_url}/commits?page={page}&branch={self.branch}"
                cmts = await self.get(url, self.token, session)
                self.logger.info(msg=f"Recived [{len(cmts)}] commits from [{page}] page for [{self.branch}] branch.")

                for commit in cmts:
                    date = self.time_zone.localize(datetime.strptime(commit['commit']['committer']['date'], self.input_format))
                    if date < start:
                        is_continue = False
                        break

                    tasks.append(asyncio.create_task(self.get_commit_info({
                        'sha': commit['sha'],
                        'Upload Date': date.isoformat(sep=' ', timespec='seconds'),
                        'Upload Date' : commit['commit']['committer']['date'],
                        'Create Date': commit['commit']['author']['date'],
                        'Message': commit['commit']['message'],
                        'Author': commit['commit']['author']['name'],
                        'Url': commit['html_url'],
                        'Files': []
                    }, session)))
                page += 1

            try:
                await asyncio.wait_for(asyncio.gather(*tasks), timeout=len(tasks) * 180)
            except asyncio.TimeoutError:
                self.logger.warning(msg="Timeout error: one or more tasks took too long to complete.")
        
        self.pull_requests.sort(key=lambda pr: datetime.strptime(pr['Merged at'], self.input_format),reverse=True)
        self.write_pull_requests()

    async def get_commit_info(self, commit, session):
        # Collect file information
        url = f"{self.base_url}/commits/{commit['sha']}"
        cmt = await self.get(url, self.token, session)
        self.logger.info(msg=f"Recived [{commit['sha']}] commit.")
        files = []
        for file in cmt['files']:
            if file['sha'] not in self.sha_exist_files:
                files.append({
                    'sha' : file['sha'],
                    'filename' : file.get('filename'),
                    'name' : file['filename'],
                    'patch' : file.get('patch'),
                    'state' : '',
                    'review': ''})
                self.sha_exist_files.append(file['sha'])
        commit['Files'] = files
        url = f"{self.base_url}/commits/{commit['sha']}/pulls"
        prs = await self.get(url, self.token, session)
        self.logger.info(msg=f"Recived [{len(prs)}] pull requests for [{commit['sha']}] commit.")

        for pr in prs:
            await self.update_pull_request(pr, commit=commit,base_url=self.base_url,token=self.token,  session=session)

    async def update_pull_request(self, pr, commit, base_url, token, session):
        exist_pr = [pull_request['number'] for pull_request in self.pull_requests]
        if pr['number'] in exist_pr:
            if commit['sha'] not in [commit['sha'] for commit in self.pull_requests[exist_pr.index(pr['number'])]['commits']]:
                self.pull_requests[exist_pr.index(pr['number'])]['commits'].append(commit)
        else:
            url = f"{base_url}/pulls/{pr['number']}"
            pull_request = await self.get(url, token, session)
            self.logger.info(msg=f"Recived [{pr['number']}] pull requests.")
            
            pull_request = {
                'number' : pull_request['number'],
                'commits' : [commit],
                'Merged by' : pull_request['merged_by']['login'],
                'Merged at' : pull_request['merged_at'],
                'Url' : pull_request['html_url'],
                'Comments' : await self.get_reviews(pr_number = pr['number'], session = session)
            }
            self.pull_requests.append(pull_request)        
            self.write_pull_requests()

            for commit in pull_request['commits']:
                for file in commit['Files']:
                    reviewed = await self.review_file(file)
                    if not reviewed:
                        commit['Files'] = [f for f in commit['Files'] if f != file]
            
            self.write_pull_requests()

    async def get_reviews(self, pr_number, session):
        url = f"{self.base_url}/pulls/{pr_number}/reviews"
        reviews =  await self.get(url, self.token, session)
        self.logger.info(msg=f"Recived [{len(reviews)}] reviews for [{pr_number}] pull request.")

        return [{
                    'Author' : review['user']['login'],
                    'Text': review['body'],
                    'State' : review['state']
                } for review in reviews]

    async def get(self, url, token, session):
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"token {token}"
        }
        attempt = 0
        while attempt < 3:
            try:
                attempt += 1    
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        raise Exception("Error in API call: " + await resp.text())
                    return await resp.json()
            except aiohttp.client_exceptions.ClientOSError as e:
                print(f'Error making request: {e}')
                await asyncio.sleep(1)
            except aiohttp.client_exceptions.ServerDisconnectedError as e:
                print(f'Server disconnected error: {e}')
                await asyncio.sleep(1)
            except Exception as e:
                print(f'Unexpected error occurred: {e}')
                await asyncio.sleep(1)