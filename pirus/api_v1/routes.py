#!env/python3
# coding: utf-8


from framework import *
from config import *
from api_v1.handlers import *







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
app.router.add_route('GET',    "/v1/www", website.home)
app.router.add_route('GET',    "/v1/config", website.get_config)
app.router.add_route('GET',    "/v1/api", website.get_api)
app.router.add_route('GET',    "/v1/db", website.get_db)
app.router.add_route('GET',    "/v1/ws", websocket.get)

app.router.add_route('GET',    "/v1/pipeline", pipeHdl.get)
app.router.add_route('POST',   "/v1/pipeline", pipeHdl.post)
app.router.add_route('DELETE', "/v1/pipeline/{pipe_id}", pipeHdl.delete)
app.router.add_route('GET',    "/v1/pipeline/{pipe_id}", pipeHdl.get_details)
app.router.add_route('GET',    "/v1/pipeline/{pipe_id}/{filename}", fileHdl.dl_pipe_file)

app.router.add_route('GET',    "/v1/run", runHdl.get)
app.router.add_route('POST',   "/v1/run", runHdl.post)
app.router.add_route('GET',    "/v1/run/{run_id}", runHdl.get_details)
app.router.add_route('GET',    "/v1/run/{run_id}/out", runHdl.get_olog)
app.router.add_route('GET',    "/v1/run/{run_id}/err", runHdl.get_elog)
app.router.add_route('GET',    "/v1/run/{run_id}/log", runHdl.get_plog)
app.router.add_route('GET',    "/v1/run/{run_id}/out/tail", runHdl.get_olog_tail)
app.router.add_route('GET',    "/v1/run/{run_id}/err/tail", runHdl.get_elog_tail)
app.router.add_route('GET',    "/v1/run/{run_id}/log/tail", runHdl.get_plog_tail)
app.router.add_route('GET',    "/v1/run/{run_id}/pause", runHdl.get_pause)
app.router.add_route('GET',    "/v1/run/{run_id}/play", runHdl.get_play)
app.router.add_route('GET',    "/v1/run/{run_id}/stop", runHdl.get_stop)
app.router.add_route('GET',    "/v1/run/{run_id}/{filename}", fileHdl.dl_run_file)

app.router.add_route('GET',    "/v1/file", fileHdl.get)
app.router.add_route('POST',   "/v1/file", fileHdl.upload_simple)
app.router.add_route('PATCH',  "/v1/bigfile", fileHdl.upload_resumable)
app.router.add_route('DELETE', "/v1/file/{file_id}", fileHdl.delete)
app.router.add_route('PUT',    "/v1/file/{file_id}", fileHdl.edit_infos)
app.router.add_route('GET',    "/v1/file/{file_id}", fileHdl.get_file_details)
app.router.add_route('GET',    "/v1/dl/f/{file_id}", fileHdl.dl_file)
#app.router.add_route('GET',    "/v1/dl/p/{pipe_id}/{filename}", fileHdl.dl_pipe_file)
#app.router.add_route('GET',    "/v1/dl/r/{run_id}/{filename}", fileHdl.dl_run_file)

#app.router.add_route('GET',    "/v1/run/notify/{run_id}/p/{complete}", runHdl.up_progress)
#app.router.add_route('GET',    "/v1/run/notify/{run_id}/s/{status}", runHdl.up_status)
app.router.add_route('POST',    "/v1/run/notify/{run_id}", runHdl.up_data)

app.router.add_static('/assets', TEMPLATE_DIR)
app.router.add_static('/db', DATABASES_DIR)
app.router.add_static('/pipelines', PIPELINES_DIR)
app.router.add_static('/files', FILES_DIR)
