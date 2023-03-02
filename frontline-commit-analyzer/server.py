import asyncio
import mimetypes
import os
import logging
from analyzer import analyze_commits, review_commit
from aiohttp import web

file_name = os.path.splitext(os.path.basename(__file__))[0]

logger = logging.getLogger(file_name)
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
    try:
        hours = int(request.query.get('hours', 12))
    except ValueError as e:
        logger.error(e)
        return web.Response(status=500, text=str(e))
    
    try:
        await analyze_commits(hours)
        return web.Response(status=200)
    except Exception as e:
        logger.error(e)
        return web.Response(status=500, text=str(e))
    
async def review(request):
    # Review commit
    sha = request.query.get('sha', -1)
    if sha == -1:
        e = 'Expected sha in query parameter'
        logger.error(e)
        return web.Response(status=500, text=str(e))
    
    try:
        return web.Response(status=200, text=await review_commit(sha))
    except Exception as e:
        logger.info(msg=f"error {e}")
        return web.Response(status=500, text=str(e))

async def init_app():
    app = web.Application()
    app.add_routes([
        web.get('/', index),
        web.get('/analyze', analyze),
        web.get('/review', review),
        web.get('/{path:.+}', static),
    ])
    return app


loop = asyncio.get_event_loop()
app = loop.run_until_complete(init_app())
web.run_app(app, port=3443)
