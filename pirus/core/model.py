#!env/python3
# coding: utf-8
import os
import datetime
import uuid
import sqlalchemy
import asyncio
import multiprocessing as mp
import json
import yaml


import tarfile
import shutil


from sqlalchemy.ext.automap import automap_base
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import ClauseElement
from sqlalchemy.orm import sessionmaker

from core.framework import RegovarException

import config as C
import ipdb





# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# DATABASE CONNECTION
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

def init_pg(user, password, host, port, db):
    '''Returns a connection and a metadata object'''
    try:
        url = 'postgresql://{}:{}@{}:{}/{}'.format(user, password, host, port, db)
        con = sqlalchemy.create_engine(url, client_encoding='utf8')
    except Exception as err:
        raise RegovarException("Unable to connect to database")
    return con
    

# Connect and map the engine to the database
Base = automap_base()
__db_engine = init_pg(C.DATABASE_USER, C.DATABASE_PWD, C.DATABASE_HOST, C.DATABASE_PORT, C.DATABASE_NAME)
try:
    Base.prepare(__db_engine, reflect=True)
    Base.metadata.create_all(__db_engine)
    Session = sessionmaker(bind=__db_engine)
except Exception as err:
    raise RegovarException("Error occured when initialising database")

__db_session = Session()
__db_pool = mp.Pool()
__async_job_id = 0
__async_jobs = {}




def private_execute_async(async_job_id, query):
    """
        Internal method used to execute query asynchronously
    """
    # As execution done in another thread, use also another db session to avoid thread conflicts
    session = Session()
    result = None
    try:
        result = session.execute(query)
        session.commit()
        session.commit() # Need a second commit to force session to commit :/ ... strange behavior when we execute(raw_sql) instead of using sqlalchemy's objects as query
        session.close()
    except Exception as err:
        session.close()
        r = RegovarException(ERR.E100001, "E100001", err)
        log_snippet(query, r)
        return (async_job_id, r)
    return (async_job_id, result)


def private_execute_callback(result):
    """
        Internal callback method for asynch query execution. 
    """
    job_id = result[0]
    result = result[1]
    # Storing result in dictionary
    __async_jobs[job_id]['result'] = result

    # Call callback if defined
    if __async_jobs[job_id]['callback']:
        __async_jobs[job_id]['callback'](job_id, result)

    # Delete job 
    del __async_jobs[async_job_id]







# =====================================================================================================================
# MODEL METHODS
# =====================================================================================================================


def get_or_create(session, model, defaults=None, **kwargs):
    """
        Generic method to get or create a SQLalchemy object from database
    """
    if defaults is None:
        defaults = {}
    try:
        query = session.query(model).filter_by(**kwargs)
        instance = query.first()
        if instance:
            return instance, False
        else:
            session.begin(nested=True)
            try:
                params = dict((k, v) for k, v in kwargs.items() if not isinstance(v, ClauseElement))
                params.update(defaults)
                instance = model(**params)
                session.add(instance)
                session.commit()
                return instance, True
            except IntegrityError as e:
                session.rollback()
                instance = query.one()
                return instance, False
    except Exception as e:
        raise e


def generic_save(obj):
    """
        generic method to save SQLalchemy object into database
    """
    try:
        s = Session.object_session(obj)
        if not s :
            s = Session()
            s.add(obj)

        obj.update_date = datetime.datetime.now()
        s.commit()
    except Exception as err:
        raise RegovarException(ERR.E100002.format(type(obj), "E100002", err))


def session():
    """
        Return the current pgsql session (SQLAlchemy)
    """
    return __db_session


def execute(query):
    """
        Synchrone execution of the query. If error occured, raise RegovarException
    """
    result = None
    try:
        result = __db_session.execute(query)
        __db_session.commit()
        __db_session.commit() # FIXME : Need a second commit to force session to commit :/ ... strange behavior when we execute(raw_sql) instead of using sqlalchemy's objects as query
    except Exception as err:
        r = RegovarException(ERR.E100001, "E100001", err)
        log_snippet(query, r)
        raise r
    return result


def execute_bw(query, callback=None):
    """
        Execute in background worker:
        Asynchrone execution of the query in an other thread. An optional callback method that take 2 arguments (job_id, query_result) can be set.
        This method return a job_id for this request that allow you to cancel it if needed
    """
    global __async_job_id, __async_jobs, __db_pool
    __async_job_id += 1
    t = __db_pool.apply_async(private_execute_async, args = (__async_job_id, query,), callback=private_execute_callback)
    __async_jobs[__async_job_id] = {"task" : t, "callback": callback, "query" : query, "start": datetime.datetime.now}
    return __async_job_id


async def execute_aio(query):
    """
        execute as coroutine
        Asynchrone execution of the query as coroutine
    """
    # Execute the query in another thread via coroutine
    loop = asyncio.get_event_loop()
    futur = loop.run_in_executor(None, private_execute_async, None, query)

    # Aio wait the end of the async task to return result
    result = await futur
    return result[1]


def cancel(async_job_id):
    """
        Cancel an asynch job running in the threads pool
    """
    if async_job_id in __async_jobs.keys():
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(__async_jobs.keys[async_job_id]["task"].cancel)
        log("Model async query (id:{}) canceled".format(async_job_id))
    else:
        war("Model unable to cancel async query (id:{}) because it doesn't exists".format(async_job_id))





# =====================================================================================================================
# MODEL DEFINITION - Build from the database (see sql scripts used to generate the database)
# =====================================================================================================================


# =====================================================================================================================
# FILE
# =====================================================================================================================
def file_init(self, loading_depth=0):
    """
        If loading_depth is > 0, children objects will be loaded. Max depth level is 2.
        Children objects of a file are :
            - job_source : set with a Job object if the file have been created by a job. 
            - jobs       : the list of jobs in which the file is used or created
        If loading_depth == 0, children objects are not loaded
    """
    self.loading_depth = min(2, loading_depth)
    self.jobs_ids = JobFile.get_jobs_ids(self.id)
    self.jobs = []
    self.job_source = None
    self.load_depth(loading_depth)
            

def file_load_depth(self, loading_depth):
    if loading_depth > 0:
        try:
            self.job_source = Job.from_id(self.job_source_id, self.loading_depth-1)
            self.jobs = JobFile.get_jobs(self.id, self.loading_depth-1)
        except Exception as err:
            raise RegovarException("File data corrupted (id={}).".format(self.id), "", err)


def file_from_id(file_id, loading_depth=0):
    """
        Retrieve file with the provided id in the database
    """
    file = __db_session.query(File).filter_by(id=file_id).first()
    if file:
        file.init(loading_depth)
    return file


def file_from_ids(file_ids, loading_depth=0):
    """
        Retrieve files corresponding to the list of provided id
    """
    files = []
    if file_ids and len(file_ids) > 0:
        files = __db_session.query(File).filter(File.id.in_(file_ids)).all()
        for f in files:
            f.init(loading_depth)
    return files


def file_to_json(self, fields=None):
    """
        Export the file into json format with requested fields
    """
    result = {}
    if fields is None:
        fields = ["id", "name", "type", "size", "upload_offset", "status", "create_date", "update_date", "tags", "job_source_id", "jobs_ids"]
    for f in fields:
        if f == "create_date" or f == "update_date":
            result.update({f: eval("self." + f + ".ctime()")})
        elif f == "jobs":
            if self.loading_depth == 0:
                result.update({"jobs" : self.jobs})
            else:
                result.update({"jobs" : [j.to_json() for j in self.jobs]})
        elif f == "job_source" and self.loading_depth > 0:
            if self.job_source:
                result.update({"job_source" : self.job_source.to_json()})
            else:
                result.update({"job_source" : self.job_source})
        else:
            result.update({f: eval("self." + f)})
    return result


def file_load(self, data):
    """
        Helper to update several paramters at the same time. Note that dynamics properties like job_source and jobs
        cannot be updated with this method. However, you can update job_source_id.
        jobs list cannot be edited from the file, each run have to be edited
    """
    try:
        if "name"          in data.keys(): self.name           = data['name']
        if "type"          in data.keys(): self.type           = data['type']
        if "path"          in data.keys(): self.path           = data['path']
        if "size"          in data.keys(): self.size           = int(data["size"])
        if "upload_offset" in data.keys(): self.upload_offset  = int(data["upload_offset"])
        if "status"        in data.keys(): self.status         = data['status']
        if "create_date"   in data.keys(): self.create_date    = data['create_date']
        if "update_date"   in data.keys(): self.update_date    = data['update_date']
        if "md5sum"        in data.keys(): self.md5sum         = data["md5sum"]
        if "tags"          in data.keys(): self.tags           = data['tags']
        if "job_source_id" in data.keys(): self.job_source_id  = int(data["job_source_id"])
        # check to reload dynamics properties
        if self.loading_depth > 0:
            self.jobs = []
            self.job_source = None
            self.load_depth(loading_depth)
        self.save()
    except Exception as err:
        raise RegovarException('Invalid input data to load.', "", err)
    return self



def file_delete(file_id):
    """
        Delete the file with the provided id in the database
    """
    __db_session.query(File).filter_by(id=file_id).delete(synchronize_session=False)


def file_new():
    """
        Create a new file and init/synchronise it with the database
    """
    f = File()
    f.save()
    f.init()
    return f


File = Base.classes.file
File.public_fields = ["id", "name", "type", "path", "size", "upload_offset", "status", "create_date", "update_date", "tags", "md5sum", "job_source_id", "jobs_ids", "job_source", "jobs"]
File.init = file_init
File.load_depth = file_load_depth
File.from_id = file_from_id
File.from_ids = file_from_ids
File.to_json = file_to_json
File.load = file_load
File.save = generic_save
File.delete = file_delete
File.new = file_new









# =====================================================================================================================
# PIPELINE
# =====================================================================================================================
def pipeline_init(self, loading_depth=0):
    """
        If loading_depth is > 0, children objects will be loaded. Max depth level is 2.
        Child object of a pipeline is :
            - "image_file" : the file of the pipeline image (if exists)
            - "jobs" property which contains the list of jobs that use the pipeline

        If loading_depth == 0, child object are not loaded, so jobs will be set with the  list of job's id
    """
    self.loading_depth = min(2, loading_depth)
    self.jobs_ids = []
    self.jobs = []
    self.image_file = None
    jobs = __db_session.query(Job).filter_by(pipeline_id=self.id).all()
    for j in jobs:
        self.jobs_ids.append(f.id)
    self.loading_depth(loading_depth)
            

def pipeline_loading_depth(self, loading_depth):
    if loading_depth > 0:
        try:
            self.image_file = File.from_id(self.image_file_id, self.loading_depth-1)
            self.jobs = []
            jobs = Job.query.filter(Job.id.in_(self.jobs_ids)).all()
            for j in jobs:
                self.jobs.append(f.init(loading_depth-1))
        except Exception as err:
            raise RegovarException("File data corrupted (id={}).".format(self.id), "", err)



def pipeline_from_id(pipeline_id, loading_depth=0):
    """
        Retrieve pipeline with the provided id in the database
    """
    pipeline = __db_session.query(Pipeline).filter_by(id=pipeline_id).first()
    pipeline.init(loading_depth)
    return pipeline


def pipeline_from_ids(pipeline_ids, loading_depth=0):
    """
        Retrieve pipelines corresponding to the list of provided id
    """
    pipelines = []
    if pipelines and len(pipelines) > 0:
        pipelines = __db_session.query(Pipeline).filter(Pipeline.id.in_(pipeline_ids)).all()
        for f in pipelines:
            f.init(loading_depth)
    return pipelines


def pipeline_to_json(self, fields=None):
    """
        Export the pipeline into json format with only requested fields
    """
    result = {}
    if fields is None:
        fields = User.public_fields
    for f in fields:
        if f == "installation_date":
            result.update({f: eval("self." + f + ".ctime()")})
        elif f == "jobs":
            if self.loading_depth == 0:
                result.update({"jobs" : [i for i in self.jobs]})
            else:
                result.update({"jobs" : [r.to_json() for r in self.jobs]})
        elif (f == "ui_form" and self.ui_form)  or ("vm_settings" and self.vm_settings):
                result.update({f : json.loads(eval("self." + f))})
        else:
            result.update({f: eval("self." + f)})
    return result


def pipeline_load(self, data):
    try:
        # Required fields
        if "name" in data.keys(): self.name = data['name']
        if "type" in data.keys(): self.type = data["type"]
        if "status" in data.keys(): self.status = int(data["status"])
        if "description" in data.keys(): self.description = int(data["description"])
        if "license" in data.keys(): self.license = data["license"]
        if "developers" in data.keys(): self.developers = data["developers"]
        if "installation_date" in data.keys(): self.installation_date = data["installation_date"]
        if "version" in data.keys(): self.version = data['version']
        if "pirus_api" in data.keys(): self.pirus_api = data["pirus_api"]
        if "vm_image" in data.keys(): self.vm_image    = data["vm_image"]
        if "vm_settings" in data.keys():
            if data['vm_settings'] : 
                self.vm_settings = json.load(data['vm_settings'])
            else: 
                self.vm_settings = data['vm_settings']
        if "ui_form" in data.keys(): 
            if data['ui_form'] : 
                self.ui_form = json.load(data['ui_form'])
            else:
                self.ui_form = data['ui_form']
        if "ui_icon" in data.keys(): self.ui_icon = data['ui_icon']

        # TODOs
        if "jobs" in data.keys(): self.jobs = data['jobs']
        
        self.save()
    except KeyError as e:
        raise RegovarException('Invalid input pipeline: missing ' + e.args[0])
    return self


def pipeline_save(self):
    vm_settings_json = self.vm_settings
    ui_form_json = self.ui_form
    if isinstance(self.vm_settings, dict): 
        self.vm_settings = json.dumps(self.vm_settings)
    if isinstance(self.ui_form, dict): 
        self.ui_form = json.dumps(self.ui_form)

    generic_save(self)

    if vm_settings_json: 
        self.vm_settings = json.loads(vm_settings_json)
    if ui_form_json: 
        self.ui_form = json.loads(ui_form_json)



Pipeline = Base.classes.pipeline
Pipeline.public_fields = ["id", "name", "type", "status", "description", "license", "developers", "installation_date", "version", "pirus_api", "vm_image", "vm_settings", "ui_form", "ui_icon", "jobs"]
Pipeline.init = pipeline_init
Pipeline.loading_depth = pipeline_loading_depth
Pipeline.from_id = pipeline_from_id
Pipeline.from_ids = pipeline_from_ids
Pipeline.to_json = pipeline_to_json
Pipeline.load = pipeline_load
Pipeline.save = pipeline_save















# =====================================================================================================================
# JOB
# =====================================================================================================================
def job_init(self, loading_depth=0):
    """
        If loading_depth is > 0, children objects will be loaded. Max depth level is 2.
        Children objects of a job are :
            - "inputs" property set with inputs files (file id are in inputs_ids property). 
            - "outputs" property set with outputs files (file id are in outputs_ids property). 

        If loading_depth == 0, children objects are not loaded, so source will be set with the id of the job if exists
    """
    self.loading_depth = min(2, loading_depth)
    self.inputs_ids = []
    self.outputs_ids = []
    self.inputs = []
    self.outputs = []

    files = __db_session.query(JobFile).filter_by(job_id=self.id).all()
    for f in files:
        if f.as_input:
            self.inputs_ids.append(f.file_id)
        else:
            self.outputs_ids.append(f.file_id)
    self.load_depth(loading_depth)
            

def job_load_depth(self, loading_depth):
    if loading_depth > 0:
        try:
            self.inputs = []
            self.outputs = []
            if len(self.inputs_ids) > 0:
                files = __db_session.query(File).filter(File.id.in_(self.inputs_ids)).all()
                for f in files:
                    f.init(loading_depth-1)
                    self.inputs.append(f)
            if len(self.outputs_ids) > 0:
                files = __db_session.query(File).filter(File.id.in_(self.outputs_ids)).all()
                for f in files:
                    f.init(loading_depth-1)
                    self.outputs.append(f)
        except Exception as err:
            raise RegovarException("File data corrupted (id={}).".format(self.id), "", err)





def job_from_id(job_id, loading_depth=0):
    """
        Retrieve job with the provided id in the database
    """
    job = __db_session.query(Job).filter_by(id=job_id).first()
    if job:
        job.init(loading_depth)
    return job


def job_from_ids(job_ids, loading_depth=0):
    """
        Retrieve jobs corresponding to the list of provided id
    """
    jobs = []
    if job_ids and len(job_ids) > 0:
        jobs = __db_session.query(Job).filter(Job.id.in_(job_ids)).all()
        for f in jobs:
            f.init(loading_depth)
    return jobs


def job_to_json(self, fields=None):
    """
        Export the job into json format with only requested fields
    """
    result = {}
    if fields is None:
        fields = ["id", "pipe_id", "config", "start_date", "update_date", "status", "progress_value", "progress_label", "inputs_ids", "outputs_ids"]
    for f in fields:
        if f == "start_date" or f == "update_date" :
            result.update({f: eval("self." + f + ".ctime()")})
        elif f == "inputs":
            if self.loading_depth == 0:
                result.update({"inputs" : [i.to_json() for i in self.inputs]})
            else:
                result.update({"inputs" : self.inputs})
        elif f == "inputs":
            if self.loading_depth == 0:
                result.update({"outputs" : [o.to_json() for o in self.outputs]})
            else:
                result.update({"outputs" : self.outputs})
        elif f == "config" and self.config:
            result.update({f: json.loads(self.config)})
        else:
            result.update({f: eval("self." + f)})
    return result


def job_load(self, data):
    try:
        # Required fields
        if "name" in data.keys(): self.name = data['name']
        if "pipe_id" in data.keys(): self.pipe_id = data['pipe_id']
        if "config" in data.keys(): self.config = data["config"]
        if "start_date" in data.keys(): self.start_date = int(data["start_date"])
        if "update_date" in data.keys(): self.update_date = int(data["update_date"])
        if "status" in data.keys(): self.status = data["status"]
        if "progress_value" in data.keys(): self.progress_value = data["progress_value"]
        if "progress_label" in data.keys(): self.progress_label = data['progress_label']
        if "inputs_ids" in data.keys(): self.inputs_ids = data["inputs_ids"]
        if "outputs_ids" in data.keys(): self.outputs_ids = data["outputs_ids"]
        self.save()

        # delete old file/job links
        __db_session.query(JobFile).filter_by(job_id=self.id).delete(synchronize_session=False)
        # create new links
        for fid in self.inputs_ids: JobFile.new(self.id, fid, True)
        for fid in self.outputs_ids: JobFile.new(self.id, fid, False)

        # check to reload dynamics properties
        if self.loading_depth > 0:
            self.inputs = []
            self.outputs = []
            self.load_depth(loading_depth)
    except KeyError as e:
        raise RegovarException('Invalid input job: missing ' + e.args[0])
    return self


def job_save(self):
    generic_save(self)

    # Todo : save job/files associations
    if hasattr(self, 'inputs') and self.inputs: 
        # clear all associations
        # save new associations
        pass
    if hasattr(self, 'outputs') and self.outputs: 
        # clear all associations
        # save new associations
        pass


def job_delete(job_id):
    """
        Delete the job with the provided id in the database
    """
    __db_session.query(Job).filter_by(id=job_id).delete(synchronize_session=False)


def job_new():
    """
        Create a new job and init/synchronise it with the database
    """
    j = Job()
    j.save()
    j.init()
    return j


Job = Base.classes.job
Job.public_fields = ["id", "pipe_id", "config", "start_date", "update_date", "status", "progress_value", "progress_label", "inputs_ids", "outputs_ids", "inputs", "outputs"]
Job.init = job_init
Job.load_depth = job_load_depth
Job.from_id = job_from_id
Job.from_ids = job_from_ids
Job.to_json = job_to_json
Job.load = job_load
Job.save = job_save
Job.new = job_new
Job.delete = job_delete








# =====================================================================================================================
# JOBFILE associations
# =====================================================================================================================
JobFile = Base.classes.job_file


def jobfile_get_jobs(file_id, loading_depth=0):
    """
        Return the list of jobs that are using the file (as input and/or output)
    """
    result = jobs = []
    jobs_ids = jobfile_get_jobs_ids(file_id)
    if len(jobs_ids) > 0:
        jobs = __db_session.query(Job).filter(Job.id.in_(jobs_ids)).all()
    for j in jobs:
        j.init(loading_depth)
        result.append(j)
    return result


def jobfile_get_inputs(job_id, loading_depth=0):
    """
        Return the list of input's files of the job
    """
    result = files = []
    files_ids = jobfile_get_inputs_ids(job_id)
    if len(files) > 0:
        files = __db_session.query(File).filter(File.id.in_(files_ids)).all()
    for f in files:
        f.init(loading_depth)
        result.append(f)
    return result


def jobfile_get_outputs(job_id, loading_depth=0):
    """
        Return the list of output's files of the job
    """
    result = files = []
    files_ids = jobfile_get_outputs_ids(job_id)
    if len(files) > 0:
        files = __db_session.query(File).filter(File.id.in_(files_ids)).all()
    for f in files:
        f.init(loading_depth)
        result.append(f)
    return result


def jobfile_get_jobs_ids(file_id):
    """
        Return the list of job's id that are using the file (as input and/or output)
    """
    result = []
    jobs = __db_session.query(JobFile).filter_by(file_id=file_id).all()
    for j in jobs:
        result.append(j.job_id)
    return result
    

def jobfile_get_inputs_ids(job_id):
    """
        Return the list of file's id that are used as input for the job
    """
    result = []
    files = __db_session.query(JobFile).filter_by(job_id=job_id, as_input=True).all()
    for f in files:
        result.append(f.file_id)
    return result


def jobfile_get_outputs_ids(job_id):
    """
        Return the list of file's id that are used as output for the job
    """
    result = []
    files = __db_session.query(JobFile).filter_by(job_id=job_id, as_input=False).all()
    for f in files:
        result.append(f.file_id)
    return result


def jobfile_new(job_id, file_id, as_input):
    """
        Create a new job-file association and save it in the database
    """
    jf = JobFile(job_id=job_id, file_id=file_id, as_input=as_input)
    jf.save()
    return jf


JobFile.get_jobs = jobfile_get_jobs
JobFile.get_inputs = jobfile_get_inputs
JobFile.get_outputs = jobfile_get_outputs
JobFile.get_jobs_ids = jobfile_get_jobs_ids
JobFile.get_inputs_ids = jobfile_get_inputs_ids
JobFile.get_outputs_ids = jobfile_get_outputs_ids
JobFile.save = generic_save
JobFile.new = jobfile_new



#A bouger dans le core ?


# Pipeline
#     @staticmethod
#     def new_from_tus(filename, file_size):
#         pipe   = Pipeline()
#         pipe.import_data({
#                 "name"          : filename,
#                 "pirus_api"     : "Unknow",
#                 "pipeline_file" : os.path.join(TEMP_DIR, str(uuid.uuid4())),
#                 "size"          : file_size,
#                 "upload_offset" : 0,
#                 "status"        : "WAITING"
#             })  
#         pipe.save()
#         pipe.url = "http://" + HOST_P + "/pipeline/" + str(pipe.id)
#         pipe.upload_url = "http://" + HOST_P + "/pipeline/upload/" + str(pipe.id)
#         pipe.save()
#         return pipe
