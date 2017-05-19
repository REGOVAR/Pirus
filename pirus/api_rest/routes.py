#!env/python3
# coding: utf-8

import aiohttp_jinja2
import jinja2
from aiohttp import web

from api_rest.handlers import *




app = web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(TEMPLATE_DIR))	


# Handlers instances
websocket = WebsocketHandler()
website = WebsiteHandler()
fileHdl = FileHandler()
jobHdl = JobHandler()
pipeHdl = PipelineHandler()

# Config server app
app['websockets'] = []

# On shutdown, close all websockets
app.on_shutdown.append(on_shutdown)




# Routes
app.router.add_route('GET',    "/",       website.home)
app.router.add_route('GET',    "/api",    website.api)
app.router.add_route('GET',    "/config", website.config)
app.router.add_route('GET',    "/db",     website.get_db)
app.router.add_route('GET',    "/db/{ref}", website.get_db)
app.router.add_route('GET',    "/db/{ref}/{bundle}", website.get_db)
app.router.add_route('GET',    "/ws",     websocket.get)

app.router.add_route('GET',    "/pipeline",                                    pipeHdl.get)
app.router.add_route('GET',    "/pipeline/{pipe_id}",                          pipeHdl.get_details)
app.router.add_route('DELETE', "/pipeline/{pipe_id}",                          pipeHdl.delete)
app.router.add_route('GET',    "/pipeline/install/{file_id}/{container_type}", pipeHdl.install)
app.router.add_route('POST',   "/pipeline/install",                            pipeHdl.install_json)
app.router.add_route('GET',    "/pipeline/{pipe_id}/{filename}",               fileHdl.dl_pipe_file)

app.router.add_route('GET',    "/job",                     jobHdl.get)
app.router.add_route('POST',   "/job",                     jobHdl.new)
app.router.add_route('GET',    "/job/{job_id}",            jobHdl.get_details)
app.router.add_route('GET',    "/job/{job_id}/pause",      jobHdl.pause)
app.router.add_route('GET',    "/job/{job_id}/start",      jobHdl.start)
app.router.add_route('GET',    "/job/{job_id}/cancel",     jobHdl.cancel)
app.router.add_route('GET',    "/job/{job_id}/monitoring", jobHdl.monitoring)
app.router.add_route('GET',    "/job/{job_id}/finalize",   jobHdl.finalize)
#app.router.add_route('GET',    "/job/{job_id}/{filename}", fileHdl.dl_job_file)

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
app.router.add_route('POST',   "/job/notify/{job_id}", jobHdl.update_status)


# Statics root for direct download
# FIXME - Routes that should be manages directly by NginX
app.router.add_static('/assets', TEMPLATE_DIR)
app.router.add_static('/dl/db/', DATABASES_DIR)
app.router.add_static('/dl/pipe/', PIPELINES_DIR)
app.router.add_static('/dl/file/', FILES_DIR)
app.router.add_static('/dl/job/', FILES_DIR)

app.router.add_route('GET',    "/dl/f/{file_id}", fileHdl.dl_file)
#app.router.add_route('GET',    "/dl/p/{file_id}", fileHdl.dl_pipeline)
#app.router.add_route('GET',    "/dl/r/{file_id}", fileHdl.dl_job)