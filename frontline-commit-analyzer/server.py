import asyncio
import mimetypes
import os
import logging
from aiohttp import web
from asyncio.subprocess import PIPE, create_subprocess_exec

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def index(request):
    # Serve index.html file
    file_path = os.path.join(os.path.dirname(__file__), 'static', 'index.html')
    with open(file_path, 'rb') as f:
        return web.Response(body=f.read(), content_type='text/html')

async def static(request):
    # Serve static files
    path = request.match_info.get('path', '')
    file_path = os.path.join(os.path.dirname(__file__), 'static', path.lstrip('/'))
    if os.path.exists(file_path) and os.path.isfile(file_path):
        with open(file_path, 'rb') as f:
            content_type, _ = mimetypes.guess_type(file_path)
            return web.Response(body=f.read(), content_type=content_type or 'application/octet-stream')
    else:
        return web.Response(status=404)

async def analyze(request):
    # Analyze data
    hours = request.query.get('hours', '12')
    analyzer_path = os.path.join(os.path.dirname(__file__), 'analyzer.py')

    try:
        proc = await create_subprocess_exec('python', analyzer_path, hours, stdout=PIPE, stderr=PIPE)                
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            logging.info(msg=stdout.decode())
            logging.warning(msg=stderr.decode())
            return web.Response(status=200)
        else:
            return web.Response(status=500)
    except Exception as e:
        logging.error(e)
        return web.Response(status=500, text=str(e))

async def init_app():
    app = web.Application()
    app.add_routes([
        web.get('/', index),
        web.get('/analyze', analyze),
        web.get('/{path:.+}', static),
    ])
    return app


loop = asyncio.get_event_loop()
app = loop.run_until_complete(init_app())
web.run_app(app, port=3443)
