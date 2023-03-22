from asyncio import get_event_loop, run, sleep
from json import dumps, load
from logging import INFO, basicConfig, getLogger
from os import environ, path
from aiohttp import ClientSession, TCPConnector, client_exceptions
from openpyxl import Workbook

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

    
    #Add date of version build
    async def start(self):
        result = []

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
                                    for build in builds.get('build'):
                                        details = await self.build(build.get('id'), session)
                                        result.append({
                                            'client': client.get('name'),
                                            'versions': build.get('number'),
                                            'time': details.get('startDate')
                                        })
        self.save(result)

    def save(self, versions):
        # with open('result.json', mode='w', encoding='UTF-8') as file:
        #     file.write(dumps(versions, indent=2, ensure_ascii=False))

        book = Workbook()
        sheet = book.active
        sheet.title = "Versions"
        for version in versions:
            sheet.append([name for column, name in version.items()])
        book.save(filename=self.version_path)

with VersionScrapper('teams.acceliplan.com') as scrapper:
    get_event_loop().run_until_complete(scrapper.start())