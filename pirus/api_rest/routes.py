#!env/python3
# coding: utf-8

import aiohttp_jinja2
import jinja2
from aiohttp import web

from core import pirus
from api_rest.handlers import *




app = web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(TEMPLATE_DIR))	


# Handlers instances
websocket = WebsocketHandler()
website = WebsiteHandler()
fileHdl = FileHandler()
runHdl = RunHandler()
pipeHdl = PipelineHandler()

# Config server app
app['websockets'] = []

# On shutdown, close all websockets
app.on_shutdown.append(on_shutdown)




# Routes
app.router.add_route('GET',    "/",          website.home)
app.router.add_route('GET',    "/www",    website.home)
app.router.add_route('GET',    "/config", website.get_config)
app.router.add_route('GET',    "/db",     website.get_db)
app.router.add_route('GET',    "/ws",     websocket.get)

app.router.add_route('GET',    "/pipeline",                      pipeHdl.get)
app.router.add_route('DELETE', "/pipeline/{pipe_id}",            pipeHdl.delete)
app.router.add_route('GET',    "/pipeline/{pipe_id}",            pipeHdl.get_details)
app.router.add_route('GET',    "/pipeline/{pipe_id}/{filename}", fileHdl.dl_pipe_file)
app.router.add_route('POST',   "/pipeline/upload",               pipeHdl.tus_upload_init)
app.router.add_route('OPTIONS',"/pipeline/upload",               pipeHdl.tus_config)
app.router.add_route('HEAD',   "/pipeline/upload/{file_id}",     pipeHdl.tus_upload_resume)
app.router.add_route('PATCH',  "/pipeline/upload/{file_id}",     pipeHdl.tus_upload_chunk)
app.router.add_route('DELETE', "/pipeline/upload/{file_id}",     pipeHdl.tus_upload_delete)

app.router.add_route('GET',    "/run",                     runHdl.get)
app.router.add_route('POST',   "/run",                     runHdl.post)
app.router.add_route('GET',    "/run/{run_id}",            runHdl.get_details)
app.router.add_route('GET',    "/run/{run_id}/out",        runHdl.get_olog)
app.router.add_route('GET',    "/run/{run_id}/err",        runHdl.get_elog)
app.router.add_route('GET',    "/run/{run_id}/out/tail",   runHdl.get_olog_tail)
app.router.add_route('GET',    "/run/{run_id}/err/tail",   runHdl.get_elog_tail)
app.router.add_route('GET',    "/run/{run_id}/io",         runHdl.get_io)
app.router.add_route('GET',    "/run/{run_id}/pause",      runHdl.get_pause)
app.router.add_route('GET',    "/run/{run_id}/play",       runHdl.get_play)
app.router.add_route('GET',    "/run/{run_id}/stop",       runHdl.get_stop)
app.router.add_route('GET',    "/run/{run_id}/monitoring", runHdl.get_monitoring)
#app.router.add_route('GET',    "/run/{run_id}/{filename}", fileHdl.dl_run_file)

app.router.add_route('GET',    "/file", fileHdl.get)
app.router.add_route('DELETE', "/file/{file_id}",        fileHdl.delete)
app.router.add_route('PUT',    "/file/{file_id}",        fileHdl.edit_infos)
app.router.add_route('GET',    "/file/{file_id}",        fileHdl.get_details)
app.router.add_route('POST',   "/file/upload",           fileHdl.tus_upload_init)
app.router.add_route('OPTIONS',"/file/upload",           fileHdl.tus_config)
app.router.add_route('HEAD',   "/file/upload/{file_id}", fileHdl.tus_upload_resume)
app.router.add_route('PATCH',  "/file/upload/{file_id}", fileHdl.tus_upload_chunk)
app.router.add_route('DELETE', "/file/upload/{file_id}", fileHdl.tus_upload_delete)

# Websockets / realtime notification
app.router.add_route('POST',   "/run/notify/{run_id}", runHdl.update_status)


# DEV/DEBUG - Routes that should be manages directly by NginX
app.router.add_static('/assets', TEMPLATE_DIR)
app.router.add_static('/db', DATABASES_DIR)
app.router.add_static('/pipelines', PIPELINES_DIR)
app.router.add_static('/files', FILES_DIR)

app.router.add_route('GET',    "/dl/f/{file_id}", fileHdl.dl_file)
#app.router.add_route('GET',    "/dl/p/{file_id}", fileHdl.dl_pipeline)
#app.router.add_route('GET',    "/dl/r/{file_id}", fileHdl.dl_run)