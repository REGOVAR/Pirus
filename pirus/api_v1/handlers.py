#!env/python3
# coding: utf-8
import ipdb; 


import os
import json
import aiohttp
import aiohttp_jinja2
import jinja2
import tarfile
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


def list_pipelines():
    return [f.export_client_data() for f in Pipeline.objects.all().order_by('-name')]


def list_files():
    return [p.export_client_data() for p in PirusFile.objects.all().order_by('-create_date')]


def list_runs(start=0, limit=10):
    return [r.export_client_data() for r in Run.objects.all().order_by('-start')[start:start+limit]]


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
            "runs"     : list_runs(), 
            "pipes"    : list_pipelines(),
            "files"    : list_files(),
            "hostname" : HOSTNAME
        }

    def get_config(self, request):
        return rest_success({
            "host" : HOST,
            "port" : PORT,
            "version" : VERSION,
            "base_url" : "http://" + HOSTNAME,
            "max_parallel_run " : LXD_MAX,
            "run_config " : LXD_HDW_CONF
        })

    def get_api(self, request):
        return rest_success({
            "TODO" : "url to the swagger and the doc for this version of the api"
        })

    def get_db(self, request):
        return rest_success([f for f in os.listdir(DATABASES_DIR) if os.path.isfile(os.path.join(DATABASES_DIR, f))])


 

class FileHandler:
    def __init__(self):
        pass

    def get(self, request):
        # 1- retrieve query parameters
        r_range  = request.match_info.get('range', "0-" + str(RANGE_DEFAULT))
        r_fields = request.match_info.get('fields', None)
        r_order  = request.match_info.get('order', None)
        r_sort   = request.match_info.get('sort', None)
        r_filter = request.match_info.get('filter', None)

        # 2- fields to extract
        fields = PirusFile.public_fields
        if r_fields is not None:
            fields = []
            for f in r_fields.split(','):
                f = f.strip().lower()
                if f in PirusFile.public_fields:
                    fields.append(f)
        if len(fields) == 0:
            return rest_error("No valid fields provided : " + request.match_info.get('fields'))

        # 3- Build json query for mongoengine
        query = {}
        if r_filter is not None:
            query = {}
            for k in fields:
                query.update({k : {'$regex': r_filter}})

        # 4- Order
        order = ['-create_date', "name"]
        if r_sort is not None and r_order is not None:
            r_sort = r_sort.split(',')
            r_order = r_order.split(',')
            if len(r_sort) == len(r_order):
                order = []
                for i in range(0, len(r_sort)):
                    f = r_sort[i].strip().lower()
                    if f in PirusFile.public_fields:
                        if r_order[i] == "desc":
                            f = "-" + f
                        order.append(f)
        order = tuple(order)

        # 5- limit
        r_range = r_range.split("-")
        offset=0
        limit=RANGE_DEFAULT
        try:
            offset = int(r_range[0])
            limit = int(r_range[1])
        except:
            return rest_error("No valid range provided : " + request.match_info.get('range') )

        # 6- Return result of the query !
        return [p.export_client_data(fields) for p in PirusFile.objects(__raw__=query).order_by(*order)[offset:limit]]




    async def upload_simple(self, request):
        name = str(uuid.uuid4())
        path = os.path.join(FILES_DIR, name)
        plog.info('I: Start file uploading : ' + path)
        # 1- Retrieve file from post request
        data = await request.post()
        uploadFile = data['uploadFile']
        comments = None
        tags = None
        if "comments" in data.keys():
            comments = data['comments'].strip()
        if "tags" in data.keys():
            tmps = data['tags'].split(',')
            tags = []
            for i in tmps:
                i2 = i.strip()
                if i2 != "":
                    tags.append(i2)
        # 2- save file on the server 
        try:
            with open(path, 'bw+') as f:
                f.write(uploadFile.file.read())
        except:
            # TODO : manage error
            raise PirusException("XXXX", "Bad pirus pipeline format : Manifest file corrupted.")
        plog.info('I: File uploading done : ' + path)
        # 3- save file on the database
        pirusfile = PirusFile()
        pirusfile.import_data({
                "name"    : uploadFile.filename,
                "type"    : os.path.splitext(uploadFile.filename)[1][1:].strip().lower(),
                "path"    : path,
                "size"    : humansize(os.path.getsize(path)),
                "status"       : "TMP", # DOWNLOADING, TMP, OK
                "create_date"  : str(datetime.datetime.now().timestamp()),
                "md5sum"       : md5(path),
                "tags"         : tags,
                "comments"     : comments
            })
        pirusfile.save()
        plog.info('I: File ' + name + ' (' + pirusfile.size + ') available at ' + path)
        return rest_success(pirusfile.export_client_data())


    def upload_resumable(self, request):
        # do something else
        return 'End of upload'

    def delete(self, request):
        return rest_success({})

    def get_details(self, request):
        id = request.match_info.get('id', -1)
        if id == -1:
            return rest_error("Unknow file id " + str(id))
        return rest_success(PirusFile.objects.get(pk=id).export_client_data())


    async def dl_file(self, request):        
        # 1- Retrieve request parameters
        id = request.match_info.get('id', -1)
        if id == -1:
            return rest_error("No file id provided")
        pirus_file = PirusFile.from_id(id)
        if pirus_file == None:
            return rest_error("File with id " + str(id) + "doesn't exits.")
        file = None
        if os.path.isfile(pirus_file.path):
            with open(pirus_file.path, 'br') as content_file:
                file = content_file.read()
        return web.Response(
            headers=MultiDict({'Content-Disposition': 'Attachment; filename='+pirus_file.name}),
            body=file
        )


    async def dl_pipe_file(self, request):
        # 1- Retrieve request parameters
        pipe_id = request.match_info.get('pipe_id', -1)
        filename = request.match_info.get('filename', None)
        if pipe_id == -1:
            return rest_error("Unknow pipeline id " + str(pipe_id))
        pipeline = Pipeline.from_id(pipe_id)
        if filename == None:
            return rest_error("No filename provided")
        path = os.path.join(pipeline.path, filename)
        file = None
        if os.path.isfile(path):
            with open(path, 'br') as content_file:
                file = content_file.read()
        return web.Response(
            headers=MultiDict({'Content-Disposition': 'Attachment; filename='+ filename}),
            body=file
        )


    async def dl_run_file(self, request):
        return rest_success({})

    def edit_infos(self, request):
        pass





class PipelineHandler:
    def __init__(self):
        pass

    def get(self, request):
        return rest_success([i for i in list_pipelines()])

    async def post(self, request):
        # 1- Retrieve pirus package from post request
        data = await request.post()
        ppackage = data['pipepck']
        # 2- save pirus package on the server plugins directory (with a random name to avoid problem if filename already exists)
        try:
            ppackage_name = str(uuid.uuid4())
            ppackage_path = os.path.join(PIPELINES_DIR, ppackage_name)
            ppackage_file = os.path.join(ppackage_path, ppackage.filename)
            os.makedirs(ppackage_path)
            with open(ppackage_file, 'bw+') as f:
                f.write(ppackage.file.read())
                os.chmod(ppackage_file, 0o777)
        except:
            # TODO : manage error
            return rest_error("Server Error : Unable to write on server disk (no space ? no right ?).")
        # 3- Handle nstall process done by model
        pipeline = None
        try:
            pipeline = Pipeline.install(ppackage_name, ppackage_path, ppackage_file)
        except Exception as error:
            # TODO : manage error
            return rest_error("Server Error : The following occure during installation of the pipeline. " + error.msg)
        os.chmod(ppackage_file, 0o664)
        # 4- Answer to te client
        if pipeline == None:
            # TODO : manage error
            rest_error("Server Error : Unexpected error occured while installing the pipeline.")

        return rest_success(pipeline.export_client_data())


    def delete(self, request):
        # 1- Retrieve pirus pipeline from post request
        pipe_id = request.match_info.get('pipe_id', -1)
        if pipe_id == -1:
            return rest_error("Unknow pipeline id " + str(pipe_id))

        try:
            pipeline = Pipeline.remove(pipe_id)
        except Exception as error:
            # TODO : manage error
            return rest_error("Server Error : The following occure during installation of the pipeline. " + error.msg)

        return rest_success("Pipeline " + str(pipe_id) + " deleted.")


    def get_details(self, request):
        pipe_id = request.match_info.get('pipe_id', -1)
        if pipe_id == -1:
            return rest_error("Unknow pipeline id " + str(pipe_id))
        return rest_success(Pipeline.objects.get(pk=pipe_id).export_client_data())




class RunHandler:
    def __init__(self):
        pass

    def get(self, request):
        return rest_success([r.export_client_data() for r in Run.objects.all().limit(10)])


    async def post(self, request):
        # 1- Retrieve data from request
        data = await request.json()
        pipe_id = data["pipeline_id"]
        config = data["config"]
        inputs = data["inputs"]

        # 2- Load pipeline from database
        pipeline = Pipeline.from_id(pipe_id)
        if pipeline is None:
            return rest_error("Unknow pipeline id " + str(pipe_id))
            

        config = { "run" : config, "pirus" : { "notify_url" : ""}}
        # 3- Enqueue run of the pipeline with celery
        try:
            cw = run_pipeline.delay(pipeline.lxd_alias, config, inputs)
            plog.info('RUNNING | New Run start : ' + str(cw.id))
        except:
            # TODO : clean filesystem
            return rest_error("Unable to run the pipeline with celery " + str(pipe_id))
        # 4- Store run information into database
        run = Run()
        run.import_data({
            "pipe_id" : pipe_id,
            "name" : config["run"]["name"],
            "celery_id" : str(cw.id),
            "start" : str(datetime.datetime.now().timestamp()),
            "status" : "WAITING",
            "config" : json.dumps(config),
            "inputs" : inputs,
            "progress" : {"value" : 0, "label" : "0%", "message" : "", "min" : 0, "max" : 0}
        })
        run.save()
        # 5- return result
        return rest_success(run.export_client_data())

    def delete(self, request):
        run_id = request.match_info.get('run_id', -1)
        print ("DELETE run/<id=" + str(run_id) + ">")
        return web.Response(body=b"DELETE run/<id>")

    def get_details(self, request):
        run_id = request.match_info.get('run_id', -1)
        run = Run.from_id(run_id)
        if run == None:
            return rest_error("Unable to find the run with id " + str(run_id))
        return rest_success(run.export_client_data())


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

    def get_olog_tail(self, request):
        run_id = request.match_info.get('run_id', -1)
        return self.download_file(run_id, "logs/out.log")

    def get_elog_tail(self, request):
        run_id = request.match_info.get('run_id', -1)
        return self.download_file(run_id, "logs/err.log")

    def get_plog_tail(self, request):
        run_id = request.match_info.get('run_id', -1)
        return self.download_file(run_id, "logs/pirus.log")

    def get_files(self, request):
        run_id  = request.match_info.get('run_id',  -1)
        id = request.match_info.get('id', -1)
        return self.download_file(run_id, "outputs/io.json")

    def get_file(self, request):
        run_id  = request.match_info.get('run_id',  -1)
        filename = request.match_info.get('filename', "")
        return self.download_file(run_id, filename)

    # async def up_progress(self, request):
    #     # 1- Retrieve data from request
    #     data = await request.json()
    #     pipe_id = data["pipeline_id"]
    #     config = data["config"]
    #     inputs = data["inputs"]
    #     run_id = request.match_info.get('run_id', -1)
    #     complete = request.match_info.get('complete', None)
    #     print("RunHandler[up_progress] : taskid=" + run_id, complete)
    #     run = Run.from_celery_id(run_id)
    #     if run is not None:
    #         p = run.progress.copy()
    #         p.update({"value" : complete, "label" : str(complete) + " %"})
    #         # TODO FIXME : workaround to force the update of dynamic field "progress" - only updating progress dictionary doesn't work :( 
    #         run.progress = 0 
    #         run.save()
    #         run.progress = p
    #         run.save()
    #         msg = '{"action":"run_progress", "data" : ' + json.dumps(run.export_client_data()) + '}'
    #         print (msg)
    #         notify_all(None, msg)
    #     return web.Response()

    # def up_status(self, request):
    #     run_id = request.match_info.get('run_id', -1)
    #     status = request.match_info.get('status', None)
    #     print("RunHandler[up_status] : taskid=" + run_id , status)
    #     run = Run.from_celery_id(run_id)
    #     if run is not None:
    #         run.status = status
    #         run.save()
    #     msg = '{"action":"run_progress", "data" : ' + json.dumps(last_runs()) + '}'
    #     notify_all(None, msg)
    #     return web.Response()

    async def up_data(self, request):
        # 1- Retrieve data from request
        data = await request.json()
        run_id = request.match_info.get('run_id', -1)
        run = Run.from_celery_id(run_id)
        if run is not None:
            if "progress" in data.keys():
                run.progress = data["progress"]
            if "status" in data.keys():
                run.status = data["status"]
            run.save()
            msg = '{"action":"run_progress", "data" : ' + json.dumps(run.export_client_data()) + '}'
            notify_all(None, msg)
        return web.Response()


    def get_pause(self, request):
        # Todo
        pass

    def get_play(self, request):
        # Todo
        pass

    def get_stop(self, request):
        # Todo
        pass



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
