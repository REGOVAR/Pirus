#!env/python3
# coding: utf-8


import os
import json
import aiohttp
import aiohttp_jinja2
import jinja2
import zipfile
import shutil
import datetime
import time
import uuid


from aiohttp import web, MultiDict
from mongoengine import *


from config import *
from framework import *
from pirus_worker import run_pipeline
from api_v1.model import *






# Common methods

def check_pipeline_package(path:str):
    # TODO
    # files mandatory : plugin.py, form.qml, manifest.json, config.json
    # check manifest.json, mandatory fields :
    pass


def plugins_available():
    return Pipeline.objects.all() 



def last_runs():
    return [r.export_data() for r in Run.objects.all().order_by('-start')[0:10]]


def plugin_running_task(task_id):
    result = execute_plugin.AsyncResult(task_id)
    return result.get()


def notify_all(src, msg):
    for ws in app['websockets']:
        if src != ws[1]:
            ws[0].send_str(msg)











# API HANDLERS

class WebsiteHandler:
    def __init__(self):
        pass

    @aiohttp_jinja2.template('home.html')
    def home(self, request):
        return {
            "cl" : list([ws[1] for ws in app['websockets']]), 
            "pr" : last_runs(), 
            "pa" : plugins_available(),
            "hostname" : HOSTNAME
        }




class PipelineHandler:
    def __init__(self):
        pass

    def get(self, request):
        return rest_success({"plugins" : [i for i in plugins_available()]})

    async def post(self, request):
        # 1- Retrieve pirus package from post request
        data = await request.post()
        print ("salue", data['pipepck'])
        ppackage = data['pipepck']
        # 2- save file into server plugins directory (with a random name to avoid problem if filename already exists)
        ppackage_name = str(uuid.uuid4())
        ppackage_path = os.path.join(PIPELINES_DIR, ppackage_name)
        ppackage_file = ppackage_path + ".zip"
        with open(ppackage_file, 'bw+') as f:
            f.write(ppackage.file.read())
        # 3- Unzip pipeline package
        os.makedirs(ppackage_path)
        zip_ref = zipfile.ZipFile(ppackage_file, 'r')
        zip_ref.extractall(ppackage_path)
        zip_ref.close()
        # 4- Check and clean module
        pdir  = ppackage_path
        if len(os.listdir(ppackage_path)) == 1 :
            pdir = os.path.join(ppackage_path, os.listdir(ppackage_path)[0])
        check_pipeline_package(pdir)
        data = json.load(open(os.path.join(pdir, 'manifest.json')))
        data.update({"path":os.path.join(PIPELINES_DIR, get_pipeline_forlder_name(data["name"]) + "_" + get_pipeline_forlder_name(data["version"]))})
        shutil.move(pdir, data["path"])
        # 5- Save pipeline into database
        pipeline = Pipeline()
        pipeline.import_data(data)
        pipeline.save()
        # 6- Clean directory and send OK response
        if (os.path.exists(ppackage_path)):
            shutil.rmtree(ppackage_path)
        os.remove(ppackage_file)
        return rest_success({"results": pipeline.export_data()})

    def delete(self, request):
        # 1- Retrieve pirus pipeline from post request
        pipe_id = request.match_info.get('pipe_id', -1)
        # 2- Check that the user is allowed to remove the package (owner or admin)
        # Todo
        # 3- Check that the pipeline is not running
        # Todo
        # 4- Remove pipeline files

        # 5- Remove pipeline informations in database
        print ("DELETE pipeline/<id=" + str(pipe_id) + ">")
        return rest_success("Uninstall of pipeline " + str(pipe_id) + " success.")

    def get_details(self, request):
        pipe_id = request.match_info.get('pipe_id', -1)
        if pipe_id == -1:
            return rest_error("Unknow pipeline id " + str(pipe_id))
        return rest_success(Pipeline.objects.get(pk=pipe_id).export_data())

    async def get_qml(self, request):
        pipe_id = request.match_info.get('pipe_id', -1)
        if pipe_id == -1:
            return rest_error("Id not found")
        pipeline = Pipeline.from_id(pipe_id)
        if pipeline is None:
            return rest_error("Unknow pipeline id " + str(pipe_id))
        qml = pipeline.get_qml()
        if qml is None:
            return rest_error("QML not found for the plugin " + str(pipe_id))
        return web.Response(
            headers=MultiDict({'Content-Disposition': 'Attachment'}),
            body=str.encode(qml)
        )

    def get_config(self, request):
        pipe_id = request.match_info.get('pipe_id', -1)
        if pipe_id == -1:
            return rest_error("Id not found")
        pipeline = Pipeline.from_id(pipe_id)
        if pipeline is None:
            return rest_error("Unknow pipeline id " + str(pipe_id))
        conf = pipeline.get_config()
        if conf is None:
            return rest_error("Config not found for the plugin " + str(pipe_id))
        return web.Response(
            headers=MultiDict({'Content-Disposition': 'Attachment'}),
            body=str.encode(conf)
        )



class RunHandler:
    def __init__(self):
        pass

    def get(self, request):
        return rest_success([r.export_data() for r in Run.objects.all().limit(10)])


    async def post(self, request):
        # 1- Retrieve data from request
        data = await request.json()
        pipe_id = data["pipeline_id"]
        config = data["config"]
        # 2- Load pipeline from database
        pipeline = Pipeline.from_id(pipe_id)
        if pipeline is None:
            return rest_error("Unknow pipeline id " + str(pipe_id))
        # 3- Enqueue run of the pipeline with celery
        try:
            cw = run_pipeline.delay("PirusSimple", config) # pipeline.path, config)
        except:
            # TODO : clean filesystem
            return rest_error("Unable to run the pipeline with celery " + str(pipe_id))
        # 4- Store run information into database
        run = Run()
        run.import_data({
            "pipe_id" : pipe_id,
            "pipe_name" : pipeline.name + " (" + pipeline.version + ") toto",
            "celery_id" : str(cw.id),
            "user_id" : pipe_id, # TODO : user id ?
            "start" : str(datetime.datetime.now().timestamp()),
            "status" : "INIT",
            "prog_val" : "0"
        })
        run.save()
        # 5- return result
        return rest_success(run.export_data())

    def delete(self, request):
        run_id = request.match_info.get('run_id', -1)
        print ("DELETE run/<id=" + str(run_id) + ">")
        return web.Response(body=b"DELETE run/<id>")

    def get_status(self, request):
        run_id = request.match_info.get('run_id', -1)
        run = Run.from_id(run_id)
        if run == None:
            return rest_error("Unable to find the run with id " + str(run_id))
        return rest_success(run.export_data())


    def download_file(self, run_id, filename, location=RUNS_DIR):
        if run_id == -1:
            return rest_error("Id not found")
        run = Run.from_id(run_id)
        if run == None:
            return rest_error("Unable to find the run with id " + str(run_id))
        path = os.path.join(location, run.celery_id, filename)

        if not os.path.exists(path):
            return rest_error("File not found. " + filename + " doesn't exists for the run " + str(run_id))
        content = ""
        with open(path, 'r') as content_file:
            content = content_file.read()
        return web.Response(
            headers=MultiDict({'Content-Disposition': 'Attachment'}),
            body=str.encode(content)
        )

    def get_olog(self, request):
        run_id = request.match_info.get('run_id', -1)
        return self.download_file(run_id, "logs/out.log")

    def get_elog(self, request):
        run_id = request.match_info.get('run_id', -1)
        return self.download_file(run_id, "logs/err.log")

    def get_plog(self, request):
        run_id = request.match_info.get('run_id', -1)
        return self.download_file(run_id, "logs/pirus.log")

    def get_files(self, request):
        run_id  = request.match_info.get('run_id',  -1)
        file_id = request.match_info.get('file_id', -1)
        return self.download_file(run_id, "outputs/io.json")

    def get_file(self, request):
        run_id  = request.match_info.get('run_id',  -1)
        filename = request.match_info.get('filename', "")
        return self.download_file(run_id, filename)

    def up_progress(self, request):
        run_id = request.match_info.get('run_id', -1)
        complete = request.match_info.get('complete', None)
        print("RunHandler[up_progress] : taskid=" + run_id, complete)
        run = Run.from_celery_id(run_id)
        if run is not None:
            run.prog_val = complete
            run.save()
        msg = '{"action":"run_progress", "data" : ' + json.dumps(last_runs()) + '}'
        notify_all(None, msg)
        return web.Response()

    def up_status(self, request):
        run_id = request.match_info.get('run_id', -1)
        status = request.match_info.get('status', None)
        print("RunHandler[up_status] : taskid=" + run_id , status)
        run = Run.from_celery_id(run_id)
        if run is not None:
            run.status = status
            run.save()
        msg = '{"action":"run_progress", "data" : ' + json.dumps(last_runs()) + '}'
        notify_all(None, msg)
        return web.Response()



class WebsocketHandler:
    async def get(self, request):
        peername = request.transport.get_extra_info('peername')
        if peername is not None:
            host, port = peername

        ws_id = "{}:{}".format(host, port)
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        print('WS connection open by', ws_id)
        app['websockets'].append((ws, ws_id))
        print (len(app['websockets']))
        msg = '{"action":"online_user", "data" : [' + ','.join(['"' + _ws[1] + '"' for _ws in app['websockets']]) + ']}'
        notify_all(None, msg)
        print(msg)

        try:
            async for msg in ws:
                if msg.tp == aiohttp.MsgType.text:
                    if msg.data == 'close':
                        print ('CLOSE MESSAGE RECEIVED')
                        await ws.close()
                    else:
                        # Analyse message sent by client and send response if needed
                        data = msg.json()
                        if data["action"] == "user_info":
                            print("WebsocketHandler", data["action"])
                            pass
                        elif msg.tp == aiohttp.MsgType.error:
                            print('ws connection closed with exception %s' % ws.exception())
        finally:
            print('WS connection closed for', ws_id)
            app['websockets'].remove((ws, ws_id))

        return ws


async def on_shutdown(app):
    print("SHUTDOWN SERVER... CLOSE ALL")
    for ws in app['websockets']:
        await ws[0].close(code=999, message='Server shutdown')
