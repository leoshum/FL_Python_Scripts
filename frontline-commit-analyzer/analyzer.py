import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta

import aiohttp

hours = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 12

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
        # Collect commit information
        page = 1
        is_continue = True
        tasks = []
        pull_requests = []
        start = datetime.today() - timedelta(hours=hours)
        while is_continue:
            url = f"{base_url}/commits?page={page}&branch={branch}"
            cmts = await get(url, token, session)
            logging.info(msg=f"Recived [{len(cmts)}] commits from [{page}] page for [{branch}] branch.")

            for commit in cmts:
                date = datetime.strptime(commit['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ')
                if date < start:
                    is_continue = False
                    break

                tasks.append(asyncio.create_task(get_commit_info({
                    'sha': commit['sha'],
                    'Upload Date': date.isoformat(sep=' ', timespec='seconds'),
                    'Author': commit['commit']['author']['name'],
                    'Url': commit['html_url'],
                    'Files': []
                }, session, pull_requests)))
            page += 1

        await asyncio.gather(*tasks)

    root_directory = os.path.dirname(sys.argv[0])
    with open(f'.{root_directory}\\prs.json','w',encoding='UTF-8') as file:
            file.write(json.dumps(pull_requests, indent=2, ensure_ascii=False))
            

async def get(url, token, session):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}"
    }
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            raise Exception("Error in API call: " + await resp.text())
        return await resp.json()

async def get_commit_info(commit, session, pull_requests):
    # Collect file information
    url = f"{base_url}/commits/{commit['sha']}"
    cmt = await get(url, token, session)
    logging.info(msg=f"Recived [{commit['sha']}] commit.")
    
    commit['Files'] = [{'sha' : file['sha'], 'patch' : file.get('patch')} for file in cmt['files']]

    url = f"{base_url}/commits/{commit['sha']}/pulls"
    prs = await get(url, token, session)
    logging.info(msg=f"Recived [{len(prs)}] pull requests for [{commit['sha']}] commit.")

    for pr in prs:
        await update_pull_request(pr, commit=commit,pull_requests=pull_requests,base_url=base_url,token=token,  session=session)

async def get_reviews(pr_number, session):
    url = f"{base_url}/pulls/{pr_number}/reviews"
    reviews =  await get(url, token, session)
    logging.info(msg=f"Recived [{len(reviews)}] reviews for [{pr_number}] pull request.")

    return [{
                'Author' : review['user']['login'],
                'Text': review['body'],
                'State' : review['state']
            } for review in reviews]


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

asyncio.get_event_loop().run_until_complete(main())