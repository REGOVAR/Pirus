#!env/python3
# coding: utf-8
import ipdb; 


import os
import json
import aiohttp

import aiohttp_jinja2
import tarfile
import datetime
import time
import uuid
import subprocess


from aiohttp import web, MultiDict
from urllib.parse import parse_qsl


from config import *
from core import *







# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# COMMON TOOLS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

def rest_success(response_data=None, pagination_data=None):
    """ 
        Build the REST success response that will encapsulate the given data (in python dictionary format)
        :param response_data:   The data to wrap in the JSON success response
        :param pagination_data: The data regarding the pagination
    """
    if response_data is None:
        results = {"success":True}
    else:
        results = {"success":True, "data":response_data}
    if pagination_data is not None:
        results.update(pagination_data)
    return web.json_response(results)



def rest_error(message:str="Unknow", code:str="0", error_id:str=""):
    """ 
        Build the REST error response
        :param message:         The short "friendly user" error message
        :param code:            The code of the error type
        :param error_id:        The id of the error, to return to the end-user. 
                                This code will allow admins to find in logs where exactly this error occure
    """
    results = {
        "success":              False, 
        "msg":                  message, 
        "error_code":   code, 
        "error_url":    ERROR_ROOT_URL + code,
        "error_id":             error_id
    }
    return web.json_response(results)



def notify_all(src, msg):
    for ws in app['websockets']:
        if src != ws[1]:
            ws[0].send_str(msg)






def process_generic_get(query_string, allowed_fields):
        # 1- retrieve query parameters
        get_params = MultiDict(parse_qsl(query_string))
        r_range  = get_params.get('range', "0-" + str(RANGE_DEFAULT))
        r_fields = get_params.get('fields', None)
        r_order  = get_params.get('order_by', None)
        r_sort   = get_params.get('order_sort', None)
        r_filter = get_params.get('filter', None)

        # 2- fields to extract
        fields = allowed_fields
        if r_fields is not None:
            fields = []
            for f in r_fields.split(','):
                f = f.strip().lower()
                if f in allowed_fields:
                    fields.append(f)
        if len(fields) == 0:
            return rest_error("No valid fields provided : " + get_params.get('fields'))

        # 3- Build json query for mongoengine
        query = {}
        if r_filter is not None:
            query = {"$or" : []}
            for k in fields:
                query["$or"].append({k : {'$regex': r_filter}})

        # 4- Order
        order = ['-create_date', "name"]
        if r_sort is not None and r_order is not None:
            r_sort = r_sort.split(',')
            r_order = r_order.split(',')
            if len(r_sort) == len(r_order):
                order = []
                for i in range(0, len(r_sort)):
                    f = r_sort[i].strip().lower()
                    if f in allowed_fields:
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
            return rest_error("No valid range provided : " + get_params.get('range') )

        # 6- Return processed data
        return fields, query, order, offset, limit











# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# MISC HANDLER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class WebsiteHandler:
    def __init__(self):
        pass

    @aiohttp_jinja2.template('home.html')
    def home(self, request):
        data = {
            "files"    : pirus.files.get(None, None, ['-create_date']),
            "pipes"    : pirus.pipelines.get(None, None, ['-name']),
            "runs"     : pirus.runs.get(None, None, ['-start']), 
            "hostname" : HOSTNAME
        }

        for f in data["files"]:
            f.update({"size" : humansize(f["size"])})


        return data

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


 








# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# REST FILE API HANDLER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class FileHandler:

    def get(self, request):
        # Generic processing of the get query
        fields, query, order, offset, limit = process_generic_get(request.query_string, PirusFile.public_fields)
        sub_level_loading = int(MultiDict(parse_qsl(request.query_string)).get('sublvl', 0))
        # Get range meta data
        range_data = {
            "range_offset" : offset,
            "range_limit"  : limit,
            "range_total"  : pirus.files.total(),
            "range_max"    : RANGE_MAX,
        }
        # Return result of the query for PirusFile 
        return rest_success(pirus.files.get(fields, query, order, offset, limit, sub_level_loading), range_data)




    def edit_infos(self, request):
        # TODO : implement PUT to edit file metadata (and remove the obsolete  "simple post" replaced by TUS upload )
        return rest_error("Not yet implemented")
        



    async def upload_simple(self, request):
        """
            "Simple" upload (synchrone and not resumable)
        """
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
            raise PirusException("Bad pirus pipeline format : Manifest file corrupted.")
        plog.info('I: File uploading done : ' + path)
        # 3- save file on the database
        pirusfile = pirus.files.register(uploadFile.filename, path, {
            "tags"          : tags,
            "comments"      : comments
        })
        return rest_success(pirusfile)



    def delete(self, request):
        file_id = request.match_info.get('file_id', "")
        try:
            return rest_success(pirus.files.delete(file_id))
        except Exception as err:
            return rest_error("Error occured : " + err)



    def get_details(self, request):
        file_id = request.match_info.get('file_id', -1)
        sub_level_loading = int(MultiDict(parse_qsl(request.query_string)).get('sublvl', 0))
        try:
            return rest_success(pirus.files.get_from_id(file_id))
        except PirusException as err:
            return rest_error("Error occured : " + err)




    # Resumable download implement the TUS.IO protocol.
    def tus_config(self, request):
        return tus_manager.options(request)

    def tus_upload_init(self, request):
        return tus_manager.creation(request)

    def tus_upload_resume(self, request):
        return tus_manager.resume(request)

    async def tus_upload_chunk(self, request):
        result = await tus_manager.patch(request)
        return result

    def tus_upload_delete(self, request):
        return tus_manager.delete_file(request)







    async def dl_file(self, request):        
        # 1- Retrieve request parameters
        id = request.match_info.get('file_id', -1)
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
        pipeline = Pipeline.from_id(pipe_id)
        if pipeline == None:
            return rest_error("No pipeline with id " + str(pipe_id))
        if filename == None:
            return rest_error("No filename provided")
        path = os.path.join(pipeline.root_path, filename)
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











# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# REST PIPELINE API HANDLER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class PipelineHandler:
    def __init__(self):
        pass

    def get(self, request):
        fields, query, order, offset, limit = process_generic_get(request.query_string, Pipeline.public_fields)
        sub_level_loading = int(MultiDict(parse_qsl(request.query_string)).get('sublvl', 0))
        # Get range meta data
        range_data = {
            "range_offset" : offset,
            "range_limit"  : limit,
            "range_total"  : Pipeline.objects.count(),
            "range_max"    : RANGE_MAX,
        }
        return rest_success([p.export_client_data(sub_level_loading, fields) for p in Pipeline.objects(__raw__=query).order_by(*order)[offset:limit]], range_data)   

    def delete(self, request):
        # 1- Retrieve pirus pipeline from post request
        pipe_id = request.match_info.get('pipe_id', -1)
        try:
            pipeline = Pipeline.remove(pipe_id)
        except Exception as error:
            # TODO : manage error
            return rest_error("Server Error : The following occure during deletion of the pipeline . " + error.msg)
        return rest_success("Pipeline " + str(pipe_id) + " deleted.")


    def get_details(self, request):
        pipe_id = request.match_info.get('pipe_id', -1)
        sub_level_loading = int(MultiDict(parse_qsl(request.query_string)).get('sublvl', 0))
        pipe = Pipeline.from_id(pipe_id)
        if pipe == None:
            return rest_error("No pipeline with id " + str(pipe_id))
        print ("PipelineHandler.get_details('" + str(pipe_id) + "', sublvl=" + str(sub_level_loading) + ")")
        return rest_success(pipe.export_client_data(sub_level_loading))


    # Resumable download implement the TUS.IO protocol.
    def tus_config(self, request):
        return tus_manager.options(request)

    def tus_upload_init(self, request):
        return tus_manager.creation(request)

    def tus_upload_resume(self, request):
        return tus_manager.resume(request)

    async def tus_upload_chunk(self, request):
        result = await tus_manager.patch(request)
        return result

    def tus_upload_delete(self, request):
        return tus_manager.delete_file(request)











# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# REST RUN API HANDLER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class RunHandler:
    def __init__(self):
        pass

    def get(self, request):
        fields, query, order, offset, limit = process_generic_get(request.query_string, Run.public_fields)
        sub_level_loading = int(MultiDict(parse_qsl(request.query_string)).get('sublvl', 0))
        # Get range meta data
        range_data = {
            "range_offset" : offset,
            "range_limit"  : limit,
            "range_total"  : Run.objects.count(),
            "range_max"    : RANGE_MAX,
        }
        return rest_success([p.export_client_data(sub_level_loading, fields) for p in Run.objects(__raw__=query).order_by(*order)[offset:limit]], range_data)


    def delete(self, request):
        run_id = request.match_info.get('run_id', -1)
        print ("DELETE run/<id=" + str(run_id) + ">")
        return web.Response(body=b"DELETE run/<id>")


    def get_details(self, request):
        run_id = request.match_info.get('run_id', -1)
        sub_level_loading = int(MultiDict(parse_qsl(request.query_string)).get('sublvl', 0))
        run = Run.from_id(run_id)
        if run == None:
            return rest_error("Unable to find the run with id " + str(run_id))
        return rest_success(run.export_client_data(sub_level_loading))


    def download_file(self, run_id, filename, location=RUNS_DIR):
        run = Run.from_id(run_id)
        if run == None:
            return rest_error("No run with id " + str(run_id))
        path = os.path.join(location, run.lxd_container, filename)

        if not os.path.exists(path):
            return rest_error("File not found. " + filename + " doesn't exists for the run " + str(run_id))
        content = ""
        if os.path.isfile(path):
            with open(path, 'br') as content_file:
                file = content_file.read()
        return web.Response(
            headers=MultiDict({'Content-Disposition': 'Attachment; filename='+filename}),
            body=file
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

    def get_io(self, request):
        run_id  = request.match_info.get('run_id',  -1)
        if run_id == -1:
            return rest_error("Id not found")
        run = Run.from_id(run_id)
        if run == None:
            return rest_error("Unable to find the run with id " + str(run_id))
        result={"inputs" : [], "outputs":[]}
        # Retrieve inputs files data of the run
        files = PirusFile.from_ids(run.inputs)
        result["inputs"] = [a.export_client_data() for a in files]
        # Retrieve outputs files data of the run
        files = PirusFile.from_ids(run.outputs)
        result["outputs"] = [a.export_client_data() for a in files]
        return rest_success(result)

    def get_file(self, request):
        run_id  = request.match_info.get('run_id',  -1)
        filename = request.match_info.get('filename', "")
        return self.download_file(run_id, filename)


    async def update_status(self, request):
        # 1- Retrieve data from request
        data = await request.json()
        run_id = request.match_info.get('run_id', -1)
        run = Run.from_id(run_id)
        if run is not None:
            if "progress" in data.keys():
                run.progress = data["progress"]
            status = run.status
            if "status" in data.keys():
                status = data["status"]
            self.set_status(run, status)

        return web.Response()


    # Update the status of the run, and according to the new status will do specific action
    # Notify also every one via websocket that run status changed
    def set_status(self, run, new_status):
        # Avoid useless notification
        # Impossible to change state of a run in error or canceled
        if (new_status != "RUNNING" and run.status == new_status) or run.status in  ["ERROR", "CANCELED"]:
            return

        # Update status
        run.status = new_status
        run.save()

        #Need to do something according to the new status ?
        # Nothing to do for status : "WAITING", "INITIALIZING", "RUNNING", "FINISHING"
        if run.status in ["PAUSE", "ERROR", "DONE", "CANCELED"]:
            next_run = Run.objects(status="WAITING").order_by('start')
            if len(next_run) > 0:
                if next_run[0].status == "PAUSE":
                    start_run.delay(str(next_run[0].id))
                else :
                    run_start.delay(str(next_run[0].id))
        elif run.status == "FINISHING":
            terminate_run.delay(str(run.id))
        # Push notification
        msg = {"action":"run_changed", "data" : [run.export_client_data()] }
        notify_all(None, json.dumps(msg))



    async def post(self, request):
        # 1- Retrieve data from request
        data = await request.json()
        pipe_id = data["pipeline_id"]
        config = data["config"]
        inputs = data["inputs"]
        config = { "run" : config, "pirus" : { "notify_url" : ""}}
        # Create the run 
        run = Run.create(pipe_id, config, inputs)
        if run is None:
            return error
        # start run
        run_start.delay(str(run.id))
        return rest_success(run.export_client_data())


    def get_pause(self, request):
        run_id  = request.match_info.get('run_id',  -1)
        if run_id == -1:
            return rest_error("Id not found")
        run = Run.from_id(run_id)
        if run == None:
            return rest_error("Unable to find the run with id " + str(run_id))
        if run.status in ["WAITING", "RUNNING"]:
            subprocess.Popen(["lxc", "pause", run.lxd_container])
            self.set_status(run, "PAUSE")
            return rest_success(run.export_client_data())
        return rest_error("Unable to pause the run " + str(run_id))


    def get_play(self, request):
        run_id  = request.match_info.get('run_id',  -1)
        if run_id == -1:
            return rest_error("Id not found")
        run = Run.from_id(run_id)
        if run == None:
            return rest_error("Unable to find the run with id " + str(run_id))
        if run.status == "PAUSE":
            subprocess.Popen(["lxc", "start", run.lxd_container])
            self.set_status(run, "RUNNING")
            return rest_success(run.export_client_data())
        return rest_error("Unable to restart the run " + str(run_id))


    def get_stop(self, request):
        run_id  = request.match_info.get('run_id',  -1)
        if run_id == -1:
            return rest_error("Id not found")
        run = Run.from_id(run_id)
        if run == None:
            return rest_error("Unable to find the run with id " + str(run_id))
        if run.status in ["WAITING", "PAUSE", "INITIALIZING", "RUNNING", "FINISHING"]:
            subprocess.Popen(["lxc", "delete", run.lxd_container, "--force"])
            self.set_status(run, "CANCELED")
            return rest_success(run.export_client_data())
        return rest_error("Unable to stop the run " + str(run_id))


    def get_monitoring(self, request):
        run_id  = request.match_info.get('run_id',  -1)
        if run_id == -1:
            return rest_error("Id not found")
        run = Run.from_id(run_id)
        if run == None:
            return rest_error("Unable to find the run with id " + str(run_id))
        if run.status in ["INITIALIZING", "FINISHING", "ERROR", "DONE", "CANCELED"]:
            return rest_error("No monitoring data for the run " + str(run_id))

        out = subprocess.check_output(["lxc", "info", run.lxd_container])
        result = {}
        for l in out.decode().split('\n'):
            data = l.split(': ')
            if data[0].strip() in ["Name","Created", "Status", "Processes", "Memory (current)", "Memory (peak)"]:
                result.update({data[0].strip(): data[1]})
                
        result.update({
            "out_tail" : subprocess.check_output(["tail", os.path.join(RUNS_DIR, run.lxd_container, "logs/out.log"), "-n", "100"]).decode(), 
            "err_tail" : subprocess.check_output(["tail", os.path.join(RUNS_DIR, run.lxd_container, "logs/err.log"), "-n", "100"]).decode()
        })
        return rest_success(result)











# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# WEBSOCKET HANDLER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
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
