import json
import os
import sys
sys.path.insert(0, 'C:\\Users\\mykha\\source\\repos\\fl_python\\FL_Python_Scripts\\frontline_website_load_time_script')
import asyncio
from os import path
import mimetypes
from aiohttp import web
from aiohttp_cors import CorsViewMixin, ResourceOptions, setup as cors_setup
import bootstrapper
import subprocess

# from .. .bootstrapper import main
#import ./../frontline-website-load-time-script/bootstrapper

root_folder = path.dirname(__file__)
path_to_websiteloadtime = path.normpath(path.join(root_folder, '..', 'frontline-website-load-time-script'))
path_to_script = path.join(path_to_websiteloadtime, 'bootstrapper.py')
path_to_files_for_websiteloadtime = path.join(path_to_websiteloadtime, 'NEED TO KNOW')
path_to_files_for_websiteloadtime = 'C:\\Users\\mykha\\source\\repos\\fl_python\\FL_Python_Scripts\\frontline-commit-analyzer'

static_folder = 'static'
websiteloadtime = 'websiteloadtime'


def get_files_for_websiteloadtime(request):
    files_and_folders = {}
    for root, directories, files in os.walk(path_to_websiteloadtime):
        for directory in directories:
            files_and_folders[directory] = []
        for file in files:
            directory = files_and_folders.get(os.path.split(root)[-1])
            if directory != None:
                directory.append(file)
    return web.Response(body=json.dumps(files_and_folders),status=200)

async def execute(request):
    body = (await request.read()).decode()
    info = json.loads(body)
    # script_name = request.query.get('script', None)
    # parameters = request.query.get('params', None)#.split(',')
    if info.get('script') == websiteloadtime:
        process = await asyncio.create_subprocess_exec(
            'python', path_to_script, info.get('parameters'),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        print(stdout.decode())
        print(stderr.decode())
        if process.returncode != 0:
            return web.Response(status=500)
        return web.Response(status=200)
    else:
        return web.Response(status=404)


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
    return app

loop = asyncio.get_event_loop()
app = loop.run_until_complete(init())
web.run_app(app, port=34443)