import asyncio
import json
import logging
import os
import pytz
from datetime import datetime, timedelta
from codeReview import CodeReviewProvider

import aiohttp

file_name = os.path.splitext(os.path.basename(__file__))[0]
root_directory = os.path.dirname(__file__)
pull_request_path = f'{root_directory}\\static\\prs.json'

input_format = '%Y-%m-%dT%H:%M:%SZ'
time_zone = pytz.utc
utc_now = datetime.now(time_zone)

token = os.environ.get('GITHUB_TOKEN')

branch = 'develop'
github_url = 'https://api.github.com'
repo = 'CW-0575-IEP'
owner = 'FrontlineEducation'
base_url = f"{github_url}/repos/{owner}/{repo}"

logger = logging.getLogger(file_name)
logging.basicConfig(level=logging.INFO)

def read_pull_requests():
    with open(pull_request_path, mode='r', encoding='UTF-8') as file:
        return json.load(file)

def write_pull_requests(pull_requests):
    with open(pull_request_path,'w',encoding='UTF-8') as file:
        file.write(json.dumps(pull_requests, indent=2, ensure_ascii=False))

async def review_commit(sha):
    pull_requests = read_pull_requests()
    for pull_request in pull_requests:
        for commit in pull_request['commits']:
            for file in commit['Files']:
                if file['sha'] == sha:
                    codereview_provider = CodeReviewProvider()
                    review = codereview_provider.get_code_review(file['patch'])
                    file['review'] = review
                    write_pull_requests(pull_requests)
                    return review
    raise Exception(f'Not found commit with sha [{sha}].' )

async def analyze_commits(hours = 12):
    start = utc_now - timedelta(hours=hours)
    
    if os.path.exists(pull_request_path):
        pull_requests = read_pull_requests()
        sha_exist_commits = [commit['sha'] for pr in pull_requests for commit in pr['commits']]
    else:
        pull_requests = []
        sha_exist_commits = []
    
    await process_commits(start, pull_requests, sha_exist_commits)

async def process_commits(start, pull_requests, sha_exist_commits):
    async with aiohttp.ClientSession() as session:
        codereview_provider = CodeReviewProvider()
        # Collect commit information
        page = 1
        is_continue = True
        tasks = []
        while is_continue:
            url = f"{base_url}/commits?page={page}&branch={branch}"
            cmts = await get(url, token, session)
            logger.info(msg=f"Recived [{len(cmts)}] commits from [{page}] page for [{branch}] branch.")

            for commit in cmts:
                date = time_zone.localize(datetime.strptime(commit['commit']['committer']['date'], input_format))
                if date < start:
                    is_continue = False
                    break
                if commit['sha'] in sha_exist_commits:
                    continue

                tasks.append(asyncio.create_task(get_commit_info({
                    'sha': commit['sha'],
                    'Upload Date': date.isoformat(sep=' ', timespec='seconds'),
                    'Upload Date' : datetime.strptime(commit['commit']['committer']['date'], input_format).isoformat(sep=' ', timespec='seconds'),
                    'Create Date': datetime.strptime(commit['commit']['author']['date'], input_format).isoformat(sep=' ', timespec='seconds'),
                    'Message': commit['commit']['message'],
                    'Author': commit['commit']['author']['name'],
                    'Url': commit['html_url'],
                    'Files': []
                }, session, pull_requests, codereview_provider)))
            page += 1

        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=len(tasks) * 60)
        except asyncio.TimeoutError:
            logger.warning(msg="Timeout error: one or more tasks took too long to complete.")
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=len(tasks) * 60)        
    
    pull_requests.sort(key=lambda pr: datetime.strptime(pr['Merged at'], input_format),reverse=True)
    write_pull_requests(pull_requests)

async def get_commit_info(commit, session, pull_requests, codereview_provider):
    # Collect file information
    url = f"{base_url}/commits/{commit['sha']}"
    cmt = await get(url, token, session)
    logger.info(msg=f"Recived [{commit['sha']}] commit.")
    files = []
    for file in cmt['files']:
        review = ""
        try:
            review = codereview_provider.get_code_review(file.get('patch'))
        except Exception as e:
            logger.info(msg=f"error {e}")
        files.append({
            'sha' : file['sha'],
            'name' : file['filename'],
            'patch' : file.get('patch'),
            'state' : 1, # 0 - bad, 1 - warning, 2 - good
            'review': review})
    commit['Files'] = files
    url = f"{base_url}/commits/{commit['sha']}/pulls"
    prs = await get(url, token, session)
    logger.info(msg=f"Recived [{len(prs)}] pull requests for [{commit['sha']}] commit.")

    for pr in prs:
        await update_pull_request(pr, commit=commit,pull_requests=pull_requests,base_url=base_url,token=token,  session=session)

async def update_pull_request(pr, commit, pull_requests, base_url, token, session):
    exist_pr = [pull_request['number'] for pull_request in pull_requests]
    if pr['number'] in exist_pr:
        pull_requests[exist_pr.index(pr['number'])]['commits'].append(commit)
    else:
        url = f"{base_url}/pulls/{pr['number']}"
        pull_request = await get(url, token, session)
        logger.info(msg=f"Recived [{pr['number']}] pull requests.")

        
        pull_requests.append({
            'number' : pull_request['number'],
            'commits' : [commit],
            'Merged by' : pull_request['merged_by']['login'],
            'Merged at' : pull_request['merged_at'],
            'Url' : pull_request['html_url'],
            'Comments' : await get_reviews(pr_number = pr['number'], session = session)
        })

async def get_reviews(pr_number, session):
    url = f"{base_url}/pulls/{pr_number}/reviews"
    reviews =  await get(url, token, session)
    logger.info(msg=f"Recived [{len(reviews)}] reviews for [{pr_number}] pull request.")

    return [{
                'Author' : review['user']['login'],
                'Text': review['body'],
                'State' : review['state']
            } for review in reviews]

async def get(url, token, session):
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