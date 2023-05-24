import json
import os
import sys
sys.path.insert(0, 'C:\\Users\\mykha\\source\\repos\\fl_python\\FL_Python_Scripts\\frontline_website_load_time_script')
import asyncio
from os import path
import mimetypes
from aiohttp import web
from aiohttp_cors import CorsViewMixin, ResourceOptions, setup as cors_setup
import re


# from .. .bootstrapper import main
#import ./../frontline-website-load-time-script/bootstrapper

def set_paths(root, folder, script):
    folder_path = path.normpath(path.join(root, '..', folder))
    return folder_path, path.join(folder_path, script)

root_folder = path.dirname(__file__)
website_load_folder, website_load_script = set_paths(root_folder, 'frontline-website-load-time-script', 'bootstrapper.py')

path_to_files_for_websiteloadtime = path.join(website_load_folder, 'NEED TO KNOW')
path_to_files_for_websiteloadtime = 'C:\\Users\\mykha\\source\\repos\\fl_python\\FL_Python_Scripts\\frontline-commit-analyzer'

version_tickets_folder, version_tickets_script = set_paths(root_folder, 'frontline-team-city-comment-scrapper', 'comments.py')

static_folder = 'static'
website_load = 'websiteloadtime'
version_tickets = 'version_tickets'


def get_files_for_websiteloadtime(request):
    files_and_folders = {}
    for root, directories, files in os.walk(website_load_folder):
        for directory in directories:
            files_and_folders[directory] = []
        for file in files:
            directory = files_and_folders.get(os.path.split(root)[-1])
            if directory != None:
                directory.append(file)
    return web.Response(body=json.dumps(files_and_folders),status=200)

def open_version_tickets_configuration():
    configuration_file = path.join(version_tickets_folder, 'configuration.json')
    with open(configuration_file, 'r', encoding='utf-8') as configuration_file:
        return json.loads(configuration_file.read())

def get_version_tickets_configuration(request):
    configuration = open_version_tickets_configuration()
    configuration = {
        "branch" : configuration.get('branch'),
        "first_version" : configuration.get('version').get('first'),
        "last_version" : configuration.get('version').get('last'),
        "branch_template" : re.findall(r'\b\w+\b', configuration.get('branch_template'))
    }
    return web.Response(body=json.dumps(configuration),status=200)

def update_version_tickets_configuration(config):
    configuration = open_version_tickets_configuration()
    
    configuration['branch'] = config.get('branch')
    configuration['version']['first'] = config.get('first_version')
    configuration['version']['last'] = config.get('last_version')

    configuration_file = path.join(version_tickets_folder, 'configuration.json')
    with open(configuration_file, 'w', encoding='utf-8') as configuration_file:
        configuration_file.write(json.dumps(configuration,ensure_ascii=False,indent=4))

async def execute_script(parameters):
    process = await asyncio.create_subprocess_exec(
        *parameters,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    print(stdout.decode())
    print(stderr.decode())
    return process.returncode

async def execute(request):
    body = (await request.read()).decode()
    info = json.loads(body)
    # script_name = request.query.get('script', None)
    # parameters = request.query.get('params', None)#.split(',')
    script_name = info.get('script')
    if script_name == website_load:
        os.chdir(website_load_folder)
        code = await execute_script(['powershell', 'python', website_load_script, info.get('parameters')])
    elif script_name == version_tickets:
        update_version_tickets_configuration(info.get('configuration'))
        code = await execute_script(['python', version_tickets_script])
    else:
        return web.Response(status=404)
    if code != 0:
        return web.Response(status=500)
    return web.Response(status=200)


    # filename = request.path[1:]
    # if not filename:
    #     filename = "index.html"
    # file_path = path.join(root_directory, static_folder, filename)
    # try:
    #     with open(file_path, "rb") as f:
    #         content = f.read()
    #         mime_type, _ = mimetypes.guess_type(file_path)
    #         headers = {"Content-Type": mime_type}
    #         return web.Response(body=content, headers=headers)
    # except FileNotFoundError:

async def init():
    app = web.Application()
    cors = cors_setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            allow_headers="*",
            allow_methods="*",
            expose_headers="*",
        )
    })
    cors.add(app.router.add_post('/execute', execute))
    cors.add(app.router.add_get('/get_files_for_websiteloadtime', get_files_for_websiteloadtime))
    cors.add(app.router.add_get('/version_tickets_configuration', get_version_tickets_configuration))
    return app

loop = asyncio.get_event_loop()
app = loop.run_until_complete(init())
web.run_app(app, port=34443)