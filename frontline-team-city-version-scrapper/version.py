from asyncio import get_event_loop, run, sleep
from json import dumps, load
from logging import INFO, basicConfig, getLogger
from os import environ, path
from aiohttp import ClientSession, TCPConnector, client_exceptions
import openpyxl
from packaging import version
from datetime import datetime

class VersionScrapper:
    def __init__(self, domain) -> None:
        self.session = None
        self.base_url = f"https://{domain}/app/rest"

        file_name = path.splitext(path.basename(__file__))[0]
        self.root_directory = path.dirname(__file__)

        self.version_path = f'{self.root_directory}\\versions.xlsx'

        with open(f'{self.root_directory}\\projects.json',mode='r',encoding='UTF-8') as configuration:
            self.configuration = load(configuration)

        self.logger = getLogger(file_name)
        basicConfig(level=INFO)

        token_name = 'TEAM_CITY_TOKEN'
        self.token = environ.get(token_name)
        if self.token is None:
            self.logger.error(msg=f"TeamCity bearer token not found in environments variable with name [{token_name}]!")
            exit()
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return

    async def get(self, endpoint, session):
        headers = {
        "Authorization" : f"Bearer {self.token}",
        "Accept" : "application/json"}

        attempt = 0
        while attempt < 3:
            try:
                attempt += 1
                async with session.get(f'{self.base_url}/{endpoint}', headers=headers) as resp:
                    if resp.status != 200:
                        raise Exception("Error in API call: " + await resp.text())
                    return await resp.json()
            except client_exceptions.ClientOSError as e:
                print(f'Error making request: {e}')
                await sleep(1)
            except client_exceptions.ServerDisconnectedError as e:
                print(f'Server disconnected error: {e}')
                await sleep(1)
            except Exception as e:
                print(f'Unexpected error occurred: {e}')
                await sleep(1)  

    async def projects(self, parent, session):
        url = f'projects/id:{parent}'
        return await self.get(url, session)
        
    async def builds(self, project, session):
        url = f'builds?locator=defaultFilter:false,buildType:{project},status:SUCCESS'#start:{start},
        return await self.get(url, session)
    
    async def build(self, build, session, fields = ['startDate']):
        url = f'builds/id:{build}?fields={",".join(fields)}'
        return await self.get(url, session)

    async def process_builds(self, builds, session):
        result = []
        major_proccessing = 0
        last_major = version.Version('0.0')

        for build in builds.get('build'):
            builds_version = version.parse(build.get('number'))
            if builds_version.minor != last_major.minor:
                last_major = builds_version
                major_proccessing += 1
                if major_proccessing > 3:
                    break
                major = {
                    'version' : '.'.join([str(builds_version.major), str(builds_version.micro), str(builds_version.minor)]),
                    'minors' : []
                }
                result.append(major)
            details = await self.build(build.get('id'), session)
            major.get('minors').append({
                'number' : builds_version.release[3],
                'time' : datetime.strptime(details.get('startDate'), '%Y%m%dT%H%M%S%z')
            })
            # result.append({
            #     'client': client.get('name'),
            #     'versions': build.get('number'),
            #     'time': details.get('startDate')
            # })
        return result

    
    #Make only date without time
    #3 Major and all minors
    async def start(self):
        result_clients = []

        async with ClientSession(connector=TCPConnector(verify_ssl=False),trust_env=True) as session:
            root_projects = await self.projects('DeployNewArchitecture', session)
            for cfg_environment in self.configuration:
                for environment in root_projects.get('projects').get('project'):

                    if environment.get('name') == cfg_environment.get('Environment'):

                        client_projects = await self.projects(environment.get('id'), session)
                        for client in client_projects.get('buildTypes').get('buildType'):
                            for cfg_client in cfg_environment.get('Clients'):

                                if client.get('name') == cfg_client:
                                    builds = await self.builds(client.get('id'), session)                                    
                                    result_clients.append({
                                        "name" : cfg_client,
                                        'majors' : await self.process_builds(builds, session)
                                    })
        self.save(result_clients)

    def save(self, clients):
        # with open('result.json', mode='w', encoding='UTF-8') as file:
        #     file.write(dumps(versions, indent=2, ensure_ascii=False))

        book = openpyxl.Workbook()
        sheet = book.active
        sheet.title = "Versions"
        current_row = 1
        for client in clients:
            minors_length = 0
            sheet.append([client.get('name')])
            majors = client.get('majors')    
            for major in majors:
                sheet.append([major.get('version')])
                minors = major.get('minors')            
                for minor in minors:
                    sheet.append([minor.get('number'), minor.get('time').strftime('%Y-%m-%d')])
                    minors_length += 1
            length = 1 + len(majors) + minors_length
            sheet.row_dimensions.group(current_row, current_row + length, hidden=False)
            current_row = length

        book.save(filename=self.version_path)

with VersionScrapper('teams.acceliplan.com') as scrapper:
    get_event_loop().run_until_complete(scrapper.start())