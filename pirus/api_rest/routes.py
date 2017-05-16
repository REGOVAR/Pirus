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
app.router.add_route('GET',    "/www",    website.home)
app.router.add_route('GET',    "/config", website.get_config)
app.router.add_route('GET',    "/db",     website.get_db)
app.router.add_route('GET',    "/db/{ref}", website.get_db)
app.router.add_route('GET',    "/db/{ref}/{bundle}", website.get_db)
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

app.router.add_route('GET',    "/run",                     jobHdl.get)
app.router.add_route('POST',   "/run",                     jobHdl.post)
app.router.add_route('GET',    "/run/{job_id}",            jobHdl.get_details)
app.router.add_route('GET',    "/run/{job_id}/out",        jobHdl.get_olog)
app.router.add_route('GET',    "/run/{job_id}/err",        jobHdl.get_elog)
app.router.add_route('GET',    "/run/{job_id}/out/tail",   jobHdl.get_olog_tail)
app.router.add_route('GET',    "/run/{job_id}/err/tail",   jobHdl.get_elog_tail)
app.router.add_route('GET',    "/run/{job_id}/io",         jobHdl.get_io)
app.router.add_route('GET',    "/run/{job_id}/pause",      jobHdl.get_pause)
app.router.add_route('GET',    "/run/{job_id}/play",       jobHdl.get_play)
app.router.add_route('GET',    "/run/{job_id}/stop",       jobHdl.get_stop)
app.router.add_route('GET',    "/run/{job_id}/monitoring", jobHdl.get_monitoring)
#app.router.add_route('GET',    "/run/{job_id}/{filename}", fileHdl.dl_run_file)

app.router.add_route('GET',    "/v1/file", fileHdl.get)
app.router.add_route('DELETE', "/v1/file/{file_id}",        fileHdl.delete)
app.router.add_route('PUT',    "/v1/file/{file_id}",        fileHdl.edit_infos)
app.router.add_route('GET',    "/v1/file/{file_id}",        fileHdl.get_details)
app.router.add_route('POST',   "/v1/file/upload",           fileHdl.tus_upload_init)
app.router.add_route('OPTIONS',"/v1/file/upload",           fileHdl.tus_config)
app.router.add_route('HEAD',   "/v1/file/upload/{file_id}", fileHdl.tus_upload_resume)
app.router.add_route('PATCH',  "/v1/file/upload/{file_id}", fileHdl.tus_upload_chunk)
app.router.add_route('DELETE', "/v1/file/upload/{file_id}", fileHdl.tus_upload_delete)

# Websockets / realtime notification
app.router.add_route('POST',   "/run/notify/{job_id}", jobHdl.update_status)


# DEV/DEBUG - Routes that should be manages directly by NginX
app.router.add_static('/assets', TEMPLATE_DIR)
app.router.add_static('/databases', DATABASES_DIR)
app.router.add_static('/pipelines', PIPELINES_DIR)
app.router.add_static('/files', FILES_DIR)

app.router.add_route('GET',    "/dl/f/{file_id}", fileHdl.dl_file)
#app.router.add_route('GET',    "/dl/p/{file_id}", fileHdl.dl_pipeline)
#app.router.add_route('GET',    "/dl/r/{file_id}", fileHdl.dl_run)