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
from core.framework.common import *
from core.framework.tus import *
from core.model import *
from core.core import core







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
        "success":      False, 
        "msg":          message, 
        "error_code":   code, 
        "error_url":    code,
        "error_id":     error_id
    }
    return web.json_response(results)



def rest_notify_all(src, msg):
    for ws in WebsocketHandler.socket_list:
        if src != ws[1]:
            ws[0].send_str(msg)

# Give to the core the delegate to call to notify all via websockets
core.notify_all = rest_notify_all





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
        order = "name"
        # if r_sort is not None and r_order is not None:
        #     r_sort = r_sort.split(',')
        #     r_order = r_order.split(',')
        #     if len(r_sort) == len(r_order):
        #         order = []
        #         for i in range(0, len(r_sort)):
        #             f = r_sort[i].strip().lower()
        #             if f in allowed_fields:
        #                 if r_order[i] == "desc":
        #                     f = "-" + f
        #                 order.append(f)
        # order = tuple(order)

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





def format_file_json(file_json):
    if "path" in file_json.keys():
        file_json["url"] = "http://{}/dl/file/{}/{}".format(HOST_P, file_json["id"], file_json["name"])
        file_json.pop("path")
    return file_json


def format_pipeline_json(pipe_json):
    if "image_file" in pipe_json.keys():
        pipe_json["image_file"] = format_file_json(pipe_json["image_file"] )
    if "documents" in pipe_json.keys():
        docs = []
        for doc in pipe_json["documents"]:
            docs.append("http://{}/dl/pipe/{}/{}".format(HOST_P, pipe_json["id"], os.path.basename(doc)))
        pipe_json["documents"] = docs
    if "jobs" in pipe_json.keys():
        jobs = []
        for job in pipe_json["jobs"]:
            jobs.append(format_job_json(job))
        pipe_json["jobs"] = jobs
    if "path" in pipe_json.keys():
        pipe_json.pop("path")
    return pipe_json



def format_job_json(job_json, include_log_tail=False):
    if job_json["pipeline"]:
        job_json["pipeline"] = format_pipeline_json(job_json["pipeline"])

    if job_json["logs"]:
        if include_log_tail: result.update({"logs_tails": {}})
        result.update({"logs": []})
        for log in job_json["logs"]:
            result["logs"].append("http://{}/dl/job/{}/logs/{}".format(HOST_P, os.path.basename(job_json["path"]), log.name))
            result["logs_tails"][log.name] = log.tail()
    if result["inputs"]:
        inputs = []
        for file in result["inputs"]:
            inputs.append(format_file_json(file))
        result["inputs"] = inputs
    if result["outputs"]:
        outputs = []
        for file in result["outputs"]:
            outputs.append(format_file_json(file))
        result["outputs"] = outputs
    return result










# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Customization of the TUS protocol for the download of pirus files
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# File TUS wrapper
class FileWrapper (TusFileWrapper):
    def __init__(self, id):
        self.file = File.from_id(id)
        if self.file is not None:
            self.id = id
            self.name = self.file.name
            self.upload_offset = self.file.upload_offset
            self.path = self.file.path
            self.size = self.file.size
            self.upload_url = "file/upload/" + str(id)
        else:
            return TusManager.build_response(code=500, body="Unknow id: {}".format(id))


    def save(self):
        try:
            f = File.from_id(self.id)
            f.upload_offset=self.upload_offset
            f.save()
        except Exception as ex:
            return TusManager.build_response(code=500, body="Unexpected error occured: {}".format(ex))


    def complete(self, checksum=None, checksum_type="md5"):
        try:
            log ('Upload of the file (id={0}) is complete.'.format(self.id))
            core.files.upload_finish(self.id, checksum, checksum_type)
        except Exception as ex:
            return TusManager.build_response(code=500, body="Unexpected error occured: {}".format(ex))


    @staticmethod
    def new_upload(request, filename, file_size):
        """ 
            Create and return the wrapper to manipulate the uploading file
        """
        pfile = core.files.upload_init(filename, file_size)
        return FileWrapper(pfile.id)



# set mapping
tus_manager.route_maping["/file/upload"] = FileWrapper


















# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# MISC HANDLER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class WebsiteHandler:
    def __init__(self):
        pass




    @aiohttp_jinja2.template('api_test.html')
    def api(self, request):
        return {
            "hostname" : HOST_P,
            "file_public_fields" : ", ".join(File.public_fields)
            }


    @aiohttp_jinja2.template('home.html')
    def home(self, request):
        data = {
            "pipes_inprogress" : [p.to_json() for p in core.pipelines.get(order='name', depth=1) if p.status in ["uploading", "pause", "installing"]],
            "files_all"        : [f.to_json() for f in core.files.get(order='create_date desc', depth=1)],
            "files_inprogress" : [f.to_json() for f in core.files.get(order='create_date desc', depth=1) if f.status in ["uploading", "pause"]],
            "pipes"            : [p.to_json() for p in core.pipelines.get(query={"status" : "ready"}, order='name', depth=1)],
            "jobs_done"        : [j.to_json() for j in core.jobs.get(order='start_date desc', depth=1) if j.status in ["error", "done", "canceled"]],
            "jobs_inprogress"  : [j.to_json() for j in core.jobs.get(order='start_date desc', depth=1) if j.status in ["waiting", "pause", "initializing", "running", "finalizing"]], 
            "hostname"         : HOST_P
        }
        for f in data["files_all"]: 
            f.update({"size" : humansize(f["size"])})

        for f in data["files_inprogress"]: 
            f.update({"size" : humansize(f["size"]), "upload_offset": humansize(f["upload_offset"]) , "progress" : round(int(f["upload_offset"]) / int(f["size"]) * 100)})

        for r in data["jobs_done"]:
            r.update({"progress_value" : r["progress_value"] * 100})

        for r in data["jobs_inprogress"]:
            r.update({"progress_value" : r["progress_value"] * 100})

        data.update({"total_inprogress" : len(data["files_inprogress"]) + len(data["pipes_inprogress"]) + len(data["jobs_inprogress"])})
        return data



    def config(self, request):
        return rest_success({
            "host" : HOST_P,
            "port" : PORT,
            "version" : VERSION,
            "base_url" : "http://{}/".format(HOST_P),
            "container_managers" : [k for k in CONTAINERS_CONFIG.keys()],
            "max_job_running" : MAX_JOB_RUNNING,
            "rest_results_max_range" : RANGE_MAX,
            "rest_results_default_range" : RANGE_DEFAULT
        })




    def get_db(self, request):
        ref = request.match_info.get('ref', None)
        bundle = request.match_info.get('bundle', None)
        
        json = {r:{} for r in os.listdir(DATABASES_DIR) if os.path.isdir(os.path.join(DATABASES_DIR, r))}
        for r in json.keys():
            json[r] = {b:{
                "size": humansize(os.path.getsize(os.path.join(DATABASES_DIR, r,b))),
                "bsize" : os.path.getsize(os.path.join(DATABASES_DIR, r,b)),
                "url" : "http://{}/databases/{}/{}".format(HOST_P, r, b),
                "path" : os.path.join(r,b)
                } for b in os.listdir(os.path.join(DATABASES_DIR, r))}

        return rest_success(json)


 








# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# REST FILE API HANDLER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 




class FileHandler:

    def get(self, request):
        # Generic processing of the get query
        fields, query, order, offset, limit = process_generic_get(request.query_string, File.public_fields)
        depth = int(MultiDict(parse_qsl(request.query_string)).get('sublvl', 0))
        # Get range meta data
        range_data = {
            "range_offset" : offset,
            "range_limit"  : limit,
            "range_total"  : File.count(),
            "range_max"    : RANGE_MAX,
        }
        # Return result of the query for PirusFile 
        files = core.files.get(fields, query, order, offset, limit, depth)
        return rest_success([format_file_json(f.to_json()) for f in files], range_data)




    async def edit_infos(self, request):
        file_id = request.match_info.get('file_id', "")
        params = await request.json()

        # TO DO !! how to retrieve json from PUT body in python :/ ...
        # file = File.from_id(file_id)
        # # By security, we don't allow user to edit several informations
        # allowed = ["name", "type", "tags"]
        # data_sane = {}
        # for key in data:
        #     if key in allowed:
        #         data_sane[key] = data[key]
        #     else:
        #         war("API REST do not allow to edit the file attribute : {}".format(key))
        # file.load(data_sane)
        # return rest_success(file.to_json())
        return rest_error("Not implemented.")


    def delete(self, request):
        file_id = request.match_info.get('file_id', "")
        try:
            f = core.files.delete(file_id)
            if f: return rest_success(f.to_json())
            else: return rest_error("Unable to find the file (id={})".format(file_id))
        except Exception as ex:
            return rest_error("Error occured : " + str(ex))



    def get_details(self, request):
        file_id = request.match_info.get('file_id', -1)
        file = File.from_id(file_id, 2)
        if not file:
            return rest_error("Unable to find the file (id={})".format(file_id))
        return rest_success(format_file_json(file.to_json(File.public_fields)))



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
        file_id = request.match_info.get('file_id', -1)
        pfile = File.from_id(file_id)
        if not pfile:
            return rest_error("File with id {} doesn't exits.".format(file_id))
        file = None
        if os.path.isfile(pfile.path):
            with open(pfile.path, 'br') as content_file:
                file = content_file.read()
        return web.Response(
            headers=MultiDict({'Content-Disposition': 'Attachment; filename='+pfile.name}),
            body=file
        )


    async def dl_pipe_file(self, request):
        # 1- Retrieve request parameters
        pipe_id = request.match_info.get('pipe_id', -1)
        filename = request.match_info.get('filename', None)
        pipeline = Pipeline.from_id(pipe_id, 1)
        if pipeline == None:
            return rest_error("No pipeline with id {}".format(pipe_id))
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









# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# REST PIPELINE API HANDLER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class PipelineHandler:
    def __init__(self):
        pass

    def get(self, request):
        fields, query, order, offset, limit = process_generic_get(request.query_string, Pipeline.public_fields)
        depth = int(MultiDict(parse_qsl(request.query_string)).get('sublvl', 0))
        # Get range meta data
        range_data = {
            "range_offset" : offset,
            "range_limit"  : limit,
            "range_total"  : Pipeline.count(),
            "range_max"    : RANGE_MAX,
        }
        pipes = core.pipelines.get(fields, query, order, offset, limit, depth)
        return rest_success([p.to_json() for p in pipes], range_data)


    def get_details(self, request):
        pipe_id = request.match_info.get('pipe_id', -1)
        pipe = Pipeline.from_id(pipe_id, 2)
        if not pipe:
            return rest_error("No pipeline with id ".format(pipe_id))

        pipe = pipe.to_json(Pipeline.public_fields)
        return rest_success(format_pipeline_json(pipe))


    def install(self, request):
        file_id = request.match_info.get('file_id', -1)
        container_type = request.match_info.get('container_type', -1)
        if container_type not in CONTAINERS_CONFIG.keys():
            return rest_error("Container manager of type {} not supported by the server.".format(container_type))
        file = File.from_id(file_id)
        if not file:
            return rest_error("Unable to find file with id {}.".format(file_id))
        if file.status not in ["uploading", "uploaded", "checked"]:
            return rest_error("File status is {}, this file cannot be used as pipeline image (status shall be \"uploading\", \"uploaded\" or \"checked\"".format(file_id))
        
        p = core.pipelines.install_init_image_local(file.path, False, {"type" : container_type})
        try:
            if core.pipelines.install(p.id, asynch=False):
                return rest_success(pipe.to_json())
        except RegovarException as ex:
            return rest_error(str(ex))
        return rest_error("Error occured during installation of the pipeline.")


    async def install_json(self, request):
        params = await request.json()
        # TO DO 
        return rest_error("Not implemented")


    def delete(self, request):
        pipe_id = request.match_info.get('pipe_id', -1)
        try:
            pipe = core.pipelines.delete(pipe_id, False)
        except Exception as ex:
            # TODO : manage error
            return rest_error("Unable to delete the pipeline with id {} : {}".format(pipe_id, str(ex)))
        return rest_success(pipe)














# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# REST JOB API HANDLER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class JobHandler:
    def __init__(self):
        pass

    def get(self, request):
        fields, query, order, offset, limit = process_generic_get(request.query_string, Job.public_fields)
        depth = int(MultiDict(parse_qsl(request.query_string)).get('sublvl', 0))
        # Get range meta data
        range_data = {
            "range_offset" : offset,
            "range_limit"  : limit,
            "range_total"  : Job.count(),
            "range_max"    : RANGE_MAX,
        }
        jobs = core.jobs.get(fields, query, order, offset, limit, depth)
        return rest_success([j.to_json() for j in jobs], range_data)


    def delete(self, request):
        job_id = request.match_info.get('job_id', "")
        try:
            return rest_success(core.jobs.delete(job_id).to_json())
        except Exception as error:
            return rest_error("Unable to delete the job (id={}) : {}".format(job_id, error.msg))


    def get_details(self, request):
        job_id = request.match_info.get('job_id', -1)
        job = Job.from_id(job_id, 2)
        if not job:
            return rest_error("Unable to find the job (id={})".format(job_id))
        return rest_success(job.to_json(Job.public_fields))


    def download_file(self, job_id, filename, location=JOBS_DIR):
        job = Job.from_id(job_id, 1)
        if job == None:
            return rest_error("Unable to find the job (id={})".format(job_id))
        path = os.path.join(job.path, filename)

        if not os.path.exists(path):
            return rest_error("File not found. {} doesn't exists for the job (id={})".format(filename, job_id))
        content = ""
        if os.path.isfile(path):
            with open(path, 'br') as content_file:
                file = content_file.read()
        return web.Response(
            headers=MultiDict({'Content-Disposition': 'Attachment; filename='+filename}),
            body=file
        )

    def get_olog(self, request):
        job_id = request.match_info.get('job_id', -1)
        return self.download_file(job_id, "logs/out.log")

    def get_elog(self, request):
        job_id = request.match_info.get('job_id', -1)
        return self.download_file(job_id, "logs/err.log")

    def get_plog(self, request):
        job_id = request.match_info.get('job_id', -1)
        return self.download_file(job_id, "logs/core.log")

    def get_olog_tail(self, request):
        job_id = request.match_info.get('job_id', -1)
        return self.download_file(job_id, "logs/out.log")

    def get_elog_tail(self, request):
        job_id = request.match_info.get('job_id', -1)
        return self.download_file(job_id, "logs/err.log")

    def get_plog_tail(self, request):
        job_id = request.match_info.get('job_id', -1)
        return self.download_file(job_id, "logs/core.log")

    def get_io(self, request):
        job_id  = request.match_info.get('job_id',  -1)
        if job_id == -1:
            return rest_error("Id not found")
        job = Job.from_id(job_id, 1)
        if job == None:
            return rest_error("Unable to find the job with id {}".format(job_id))
        result={
            "inputs" : [f.to_json() for f in job.inputs],
            "outputs": [f.to_json() for f in job.outputs],
        }
        return rest_success(result)

    def get_file(self, request):
        job_id  = request.match_info.get('job_id',  -1)
        filename = request.match_info.get('filename', "")
        return self.download_file(job_id, filename)


    async def update_status(self, request):
        # 1- Retrieve data from request
        data = await request.json()
        job_id = request.match_info.get('job_id', -1)
        try:
            if "status" in data.keys():
                core.jobs.set_status(job_id, data["status"])
            job = Job.from_id(job_id)
            job.load(data)
        except Exception as ex:
            return rest_error("Unable to update information for the jobs with id {}. {}".format(job_id, ex))

        return rest_success(job.to_json())




    async def new(self, request):
        # 1- Retrieve data from request
        try:
            data = await request.json()
            data = json.loads(data)
        except Exception as ex:
            return rest_error("Error occured when retriving json data to start new job. {}".format(ex))
        pipe_id = data["pipeline_id"]
        config = data["config"]
        inputs = data["inputs"]
        # Create the job 
        try:
            job = core.jobs.new(pipe_id, config, inputs, asynch=True)
        except Exception as ex:
            return rest_error("Error occured when initializing the new job. {}".format(ex))
        if job is None:
            return rest_error("Unable to create a new job.")
        return rest_success(job.to_json())


    def pause(self, request):
        job_id  = request.match_info.get('job_id',  -1)
        try:
            core.jobs.pause(job_id)
        except Exception as ex:
            return rest_error("Unable to pause the job {}. {}".format(job.id, ex))
        return rest_success()


    def start(self, request):
        job_id  = request.match_info.get('job_id', -1)
        try:
            core.jobs.play(job_id)
        except Exception as ex:
            return rest_error("Unable to start the job {}. {}".format(job.id, ex))
        return rest_success()


    def cancel(self, request):
        job_id  = request.match_info.get('job_id',  -1)
        try:
            core.jobs.stop(job_id)
        except Exception as ex:
            return rest_error("Unable to stop the job {}. {}".format(job.id, ex))
        return rest_success()


    def monitoring(self, request):
        job_id  = request.match_info.get('job_id',  -1)
        try:
            job = core.jobs.monitoring(job_id)
        except Exception as ex:
            return rest_error("Unable to retrieve monitoring info for the jobs with id={}. {}".format(job_id, ex))
        if job:
            rest_success(format_job_json(job.to_json(), True))
        return rest_error("Unable to get monitoring information for the job {}.".format(job_id))


    def finalize(self, request):
        job_id  = request.match_info.get('job_id', -1)
        try:
            core.jobs.finalize(job_id, False)
        except Exception as ex:
            return rest_error("Unable to finalize the job {}. {}".format(job_id, ex))
        return rest_success(format_job_json(Job.from_id(job_id)))








# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# WEBSOCKET HANDLER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class WebsocketHandler:
    socket_list = []


    async def get(self, request):
        peername = request.transport.get_extra_info('peername')
        if peername is not None:
            host, port = peername

        ws_id = "{}:{}".format(host, port)
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        print('WS connection open by', ws_id)
        WebsocketHandler.socket_list.append((ws, ws_id))
        msg = '{"action":"online_user", "data" : [' + ','.join(['"' + _ws[1] + '"' for _ws in WebsocketHandler.socket_list]) + ']}'
        rest_notify_all(None, msg)

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
            WebsocketHandler.socket_list.remove((ws, ws_id))

        return ws











async def on_shutdown(app):
    print("SHUTDOWN SERVER... CLOSE ALL")
    for ws in WebsocketHandler.socket_list:
        await ws[0].close(code=999, message='Server shutdown')
