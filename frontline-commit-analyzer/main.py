import base64
import json
from datetime import datetime, timedelta
import os

import requests
from unidiff import PatchSet


def get(url, token):
        headers = {
                "Accept" : "application/vnd.github+json",
                "Authorization" : f"token {token}"
        }

        response = requests.get(
                url = url,
                headers = headers)
        
        return json.loads(response.text)

days = 1
branch = 'develop'
token = os.environ.get('GITHUB_TOKEN')

github_url = 'https://api.github.com'
repo = 'CW-0575-IEP'
owner = 'FrontlineEducation'
base_url = f"{github_url}/repos/{owner}/{repo}"
#example_commit_sha = 'a8a56d25ee52d402e4a078d9a42083013e4cc40c'
#f"{base_url}/repos/{owner}/{repo}/compare/8852bc6c8aef52a0247207b0843c74fbc8cbc46b...32611805a8477726ad8c59d6b3ba1980a4d7e09c"


start = datetime.today() - timedelta(days=days)
#date = "2023-02-01T00:00:00Z"

page = 1
is_continue = True
commits = [] 
while is_continue:
        #Collect commit information
        url = f"{base_url}/commits?page={page}&branch={branch}"
        #?until={date.isoformat(sep='T',timespec='seconds')}Z
        cmts = get(url, token)

        url = f"{base_url}/commits?page={page}"
        cmts = get(url, token)
        for commit in cmts:
                date = datetime.strptime(commit['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ')
                if date < start:
                        is_continue = False
                        break
                commits.append({
                        'sha' : commit['sha'],
                        'Upload Date' : date.isoformat(sep=' ',timespec='seconds'),
                        'Author' : commit['commit']['author']['name'],
                        'Files' : []
                })

#decoded = base64.b64decode(body['content'])

#Get reviever
#Get comment
pull_requests = []
for commit in commits:
        #Collect file information
        url = f"{base_url}/commits/{commit['sha']}"
        cmt = get(url, token)
        commit['Files'] = [{'sha' : file['sha'], 'patch' : file.get('patch')} for file in cmt['files']]
        #patch = body['files'][0]['patch']
        #patch = "diff --git a/.gitignore b/.gitignore\nnew file mode 100644\nindex 0000000..017f622\n--- /dev/null\n+++ b/.gitignore\n" + patch
        #patched = PatchSet(patch)
        #hunk = patched[0][0]
        #line = patched[0][0][0]

        url = f"{base_url}/commits/{commit['sha']}/pulls"
        prs = get(url, token)

        #Add check for if this pr is merged
        #Add link to commit
        for pr in prs:
                url = f"{base_url}/pulls/{pr['number']}"
                pull_request = get(url, token)

                url = f"{base_url}/pulls/{pr['number']}/reviews"
                reviews = get(url, token)

                comments = []
                for review in reviews:
                        comments.append(review['body'])
                #/repos/{owner}/{repo}/pulls/comments/{comment_id}
                pull_requests.append({
                        'number' : pull_request['number'],
                        'commit' : commit,
                        'Merged by' : pull_request['merged_by']['login'],
                        'Comments' : comments
                        })

with open('.\\prs.json','w',encoding='UTF-8') as file:
        file.write(json.dumps(pull_requests, indent=2, ensure_ascii=False))