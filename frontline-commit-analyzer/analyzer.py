import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
import sys

import aiohttp

async def get(url, token, session):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}"
    }
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            raise Exception("Error in API call: " + await resp.text())
        return await resp.json()

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
        commits = []
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
                commits.append({
                    'sha': commit['sha'],
                    'Upload Date': date.isoformat(sep=' ', timespec='seconds'),
                    'Author': commit['commit']['author']['name'],
                    'Url': commit['html_url'],
                    'Files': []
                })

        pull_requests = []
        tasks = []
        for commit in commits:
            task = asyncio.create_task(get_commit_info(commit, session, pull_requests))
            tasks.append(task)
        await asyncio.gather(*tasks)

    root_directory = os.path.dirname(sys.argv[0])
    with open(f'{root_directory}\\prs.json','w',encoding='UTF-8') as file:
            file.write(json.dumps(pull_requests, indent=2, ensure_ascii=False))

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

async def update_pull_request(pr, commit, pull_requests, base_url, token, session):
    exist_pr = [pull_request['number'] for pull_request in pull_requests]
    if pr['number'] in exist_pr:
        pull_requests[exist_pr.index(pr['number'])]['commits'].append(commit)
    else:
        url = f"{base_url}/pulls/{pr['number']}"
        pull_request = await get(url, token, session)
        logging.info(msg=f"Recived [{pr['number']}] pull requests.")

        url = f"{base_url}/pulls/{pr['number']}/reviews"
        reviews =  await get(url, token, session)
        logging.info(msg=f"Recived [{len(reviews)}] reviews for [{pr['number']}] pull request.")

        comments = []
        for review in reviews:
            comments.append({
                'Author' : review['user']['login'],
                'Text': review['body'],
                'State' : review['state']
            })
        pull_requests.append({
            'number' : pull_request['number'],
            'commits' : [commit],
            'Merged by' : pull_request['merged_by']['login'],
            'Url' : pull_request['html_url'],
            'Comments' : comments
        })
    logging.info(f"Processing pull request: {pr['number']}")


asyncio.run(main())
