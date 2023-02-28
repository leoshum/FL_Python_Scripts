import asyncio
import json
import logging
import os
import sys
import pytz
from datetime import datetime, timedelta
from codeReview import CodeReviewProvider

import aiohttp

hours = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 12
hours = 2

input_format = '%Y-%m-%dT%H:%M:%SZ'
time_zone = pytz.utc
utc_now = datetime.now(time_zone)
start = utc_now - timedelta(hours=hours)

branch = 'develop'
token = os.environ.get('GITHUB_TOKEN')

github_url = 'https://api.github.com'
repo = 'CW-0575-IEP'
owner = 'FrontlineEducation'
base_url = f"{github_url}/repos/{owner}/{repo}"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def main():
    async with aiohttp.ClientSession() as session:
        codereview_provider = CodeReviewProvider()
        # Collect commit information
        page = 1
        is_continue = True
        tasks = []
        pull_requests = []
        while is_continue:
            url = f"{base_url}/commits?page={page}&branch={branch}"
            cmts = await get(url, token, session)
            logging.info(msg=f"Recived [{len(cmts)}] commits from [{page}] page for [{branch}] branch.")

            for commit in cmts:
                date = time_zone.localize(datetime.strptime(commit['commit']['committer']['date'], input_format))
                if date < start:
                    is_continue = False
                    break

                tasks.append(asyncio.create_task(get_commit_info({
                    'sha': commit['sha'],
                    'Upload Date': date.isoformat(sep=' ', timespec='seconds'),
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
            print("Timeout error: one or more tasks took too long to complete.")
        

    root_directory = os.path.dirname(__file__)
    with open(f'{root_directory}\\client_app\\public\\prs.json','w',encoding='UTF-8') as file:
            file.write(json.dumps(pull_requests, indent=2, ensure_ascii=False))

async def get_commit_info(commit, session, pull_requests, codereview_provider):
    # Collect file information
    url = f"{base_url}/commits/{commit['sha']}"
    cmt = await get(url, token, session)
    logging.info(msg=f"Recived [{commit['sha']}] commit.")
    files = []
    for file in cmt['files']:
        review = ""
        try:
            review = codereview_provider.get_code_review(file.get('patch'))
        except Exception as e:
            logging.info(msg=f"error {e}")
        files.append({
            'sha' : file['sha'],
            'name' : file['filename'],
            'patch' : file.get('patch'),
            'review': review})
    commit['Files'] = files
    url = f"{base_url}/commits/{commit['sha']}/pulls"
    prs = await get(url, token, session)
    logging.info(msg=f"Recived [{len(prs)}] pull requests for [{commit['sha']}] commit.")

    for pr in prs:
        await update_pull_request(pr, commit=commit,pull_requests=pull_requests,base_url=base_url,token=token,  session=session)

async def update_pull_request(pr, commit, pull_requests, base_url, token, session):
    exist_pr = [pull_request['number'] for pull_request in pull_requests]
    if pr['number'] in exist_pr:
        pull_requests[exist_pr.index(pr['number'])]['commits'].append(commit)
    else:
        url = f"{base_url}/pulls/{pr['number']}"
        pull_request = await get(url, token, session)
        logging.info(msg=f"Recived [{pr['number']}] pull requests.")

        
        pull_requests.append({
            'number' : pull_request['number'],
            'commits' : [commit],
            'Merged by' : pull_request['merged_by']['login'],
            'Url' : pull_request['html_url'],
            'Comments' : await get_reviews(pr_number = pr['number'], session = session)
        })

async def get_reviews(pr_number, session):
    url = f"{base_url}/pulls/{pr_number}/reviews"
    reviews =  await get(url, token, session)
    logging.info(msg=f"Recived [{len(reviews)}] reviews for [{pr_number}] pull request.")

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

asyncio.get_event_loop().run_until_complete(main())