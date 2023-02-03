import json
import sys
from datetime import datetime

import requests
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from packaging import version


def getJson(url: str):
    headers = { "Accept" : "application/json" }
    response = get(url, headers = headers)
    return json.loads(response)

def get(url: str, headers = {}):
    headers.update({"Authorization" : f"Bearer {token}"})

    response = requests.get(
        url = url,
        verify = False,
        headers = headers)

    return response.text

def updateLength(value, width, name):
    length = len(value)
    if length > width[name]:
        width[name] = length

configuration_file_name = "configuration.json"

with open(configuration_file_name) as configuration_file:
    configuration = json.loads(configuration_file.read())

token = configuration['token']
ticket_match = "https://frontlinetechnologies.atlassian.net/browse/CW0575-"
ticket_number_length = 5

from_version = version.parse(configuration['version']['first'])
to_version = version.parse(configuration['version']['last'])

baseurl = f"https://{configuration['host']}/app/rest"

comment_file_name = f"{from_version.__str__()}-{to_version.__str__()}.xlsx"

branch = sys.argv[0]
if branch == None:
    branch = configuration['branch']

if branch == 'prod' or branch == 'production' or branch == 'main':
    branch = 'Production'
    job_id = 'BuildNewArchitecture_Main_BuildVersion'
elif branch == 'release':
    branch = 'Release'
    job_id = 'BuildNewArchitecture_TagFix_BuildVersion'
elif branch == 'develop' or branch == 'dev':
    branch = 'Develop'
    job_id = 'BuildNewArchitecture_Trunk_BuildVersion'        

book = Workbook()
sheet = book.active

sheet.title = "Comments"
sheet.append([branch])
width = {
    'Version' : 0,
    'Build Date' : 0,
    'Author' : 0,
    'Commit Date' : 0,
    'Jira Ticket' : 0,
    'Comment' : 0
}
sheet.append(['Version','Build Date','Author','Commit Date','Jira Ticket','Comment'])

start = 0
current_version = from_version
while current_version >= from_version:

    url = f"{baseurl}/builds?locator=defaultFilter:false,start:{start},buildType:{job_id}"
    response = getJson(url)
    for build in response['build']:

        current_version = version.parse(build['number'])
        if current_version >= from_version and current_version <= to_version:
            url = f"{baseurl}/changes?locator=build:(id:{build['id']})&fields=change(username,date,comment)"
            response = getJson(url)

            updateLength(build['number'], width, 'Version')
            build_date = str(datetime.strptime(build['finishOnAgentDate'][0:15], '%Y%m%dT%H%M%S'))
            updateLength(build_date, width, 'Build Date')
            
            for change in response['change']:
                
                change_date = str(datetime.strptime(change['date'][0:15], '%Y%m%dT%H%M%S'))

                change['comment'] = change['comment'].replace('\n', '')
                if ticket_match in change['comment']:
                    ticket = change['comment'][change['comment'].index(ticket_match):len(ticket_match)+ticket_number_length]
                    comment = change['comment'][len(ticket_match)+ticket_number_length:]
                else:
                    ticket = ''
                    comment = change['comment']


                updateLength(change['username'], width, 'Author')
                updateLength(change_date, width, 'Commit Date')
                updateLength(ticket, width, 'Jira Ticket')
                updateLength(comment, width, 'Comment')
                sheet.append([build['number'], build_date, change['username'], change_date, ticket, comment])
    start += 100

for i, column_width in enumerate(width.values(),1):  # ,1 to start at 1
    sheet.column_dimensions[get_column_letter(i)].width = column_width + 3

book.save(filename=comment_file_name)