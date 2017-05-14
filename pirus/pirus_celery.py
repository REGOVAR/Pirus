#!env/python3
# coding: utf-8 
import ipdb; 

import os
import sys
import time
import requests
import json
import datetime
import pylxd
import subprocess
import shutil
import uuid
import hashlib

from celery import Celery, Task
from config import *







# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# INIT OBJECTS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# CELERY 
app = Celery('pirus_celery')
app.conf.update(
    BROKER_URL = 'amqp://guest@localhost',
    CELERY_RESULT_BACKEND = 'rpc',
    CELERY_RESULT_PERSISTENT = False,

    CELERY_TASK_SERIALIZER = 'json',
    CELERY_ACCEPT_CONTENT = ['json'],
    CELERY_RESULT_SERIALIZER = 'json',
    CELERY_INCLUDE = ['pirus_celery'],
    CELERY_TIMEZONE = 'Europe/Paris',
    CELERY_ENABLE_UTC = True,
)

# LXD
lxd_client = pylxd.Client()










class PirusTask(Task):
    """Task that sends notification on completion."""
    abstract = True

    notify_url = None
    run_path   = ""

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        #data = {'clientid': kwargs['clientid'], 'result': retval}
        #requests.get(NOTIFY_URL, data=data)
        pass

    def dump_context(self):
        print('  Context : Executing task id {0.id}, args: {0.args!r} kwargs: {0.kwargs!r}'.format(self.request))


    def notify_status(self, status:str):
        if (self.notify_url is not None and self.notify_url != ""):
            requests.post(self.notify_url, data = '{"status": "'+status+'"}' )
        else :
            self.error("Try to notify status but no url defined : " + status)

    def error(self, msg:str, error_code:int=500):
        # TODO : some log ?...
        print(error_code + " : " + msg)
        self.notify_status('ERROR')
        return error_code


    def hashfile(self, afile, hasher, blocksize=65536):
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
        return hasher.digest()







@app.task(base=PirusTask, queue='PirusQueue', bind=True)
def start_run(self, run_id):
    from core.model import Run, PirusFile, Pipeline

    run = Run.from_id(run_id)
    if run is None :
        # TODO : log error
        return

    self.notify_url = run.notify_url
    print(self.notify_url)


    print("WAITING !")
    self.notify_status("WAITING")

    # Check that all inputs files are ready to be used
    for file_id in run.inputs:
        f = PirusFile.from_id(file_id)
        if f is None :
            return self.error('Inputs file deleted before the start of the run. Run aborded.')
        if f.status not in ["CHECKED", "UPLOADED"]:
            # inputs not ready, we keep the run in the waiting status
            print("INPUTS of the run not ready. waiting")
            return 1
        
    # Inputs files ready to use, looking for lxd resources now
    # count = 0
    # for lxd_container in lxd_client.containers.all():
    #     if lxd_container.name.startswith(LXD_CONTAINER_PREFIX) and lxd_container.status == 'Running':
    #         count += 1
    count = len(Run.objects(status="RUNNING")) + len(Run.objects(status="INITIALIZING")) + len(Run.objects(status="FINISHING"))
    if len(Run.objects(status="RUNNING")) >= LXD_MAX:
        # too many run in progress, we keep the run in the waiting status
        print("To many run in progress, we keep the run in the waiting status")
        return 1


    print("INITIALIZING !")
    self.notify_status("INITIALIZING")

    #LXD ready ! Prepare filesystem of the server to host lxc container files
    root_path    = os.path.join(RUNS_DIR, run.lxd_container)
    inputs_path  = os.path.join(root_path, "inputs")
    outputs_path = os.path.join(root_path, "outputs")
    logs_path    = os.path.join(root_path, "logs")

    # Init directories
    if not os.path.exists(inputs_path):
        os.makedirs(inputs_path)
    if not os.path.exists(outputs_path):
        os.makedirs(outputs_path)
        os.chmod(outputs_path, 0o777)
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)
        os.chmod(logs_path, 0o777)

    # Put inputs files in the inputs directory of the run
    conf_file = os.path.join(inputs_path, "config.json")
    data = json.loads(run.config)
    with open(conf_file, 'w') as f:
        f.write(json.dumps(data, sort_keys=True, indent=4))
        os.chmod(conf_file, 0o777)

    for file_id in run.inputs:
        f = PirusFile.from_id(file_id)
        link_path = os.path.join(inputs_path, f.name)
        os.link(f.path, link_path)
        os.chmod(link_path, 0o644)

    # Setting up the lxc container for the run
    try:
        pipeline = Pipeline.from_id(run.pipeline_id)
        # create run file
        run_file = os.path.join(root_path, "start_" + run.lxd_container + ".sh")
        print(run_file)
        with open(run_file, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write(pipeline.lxd_run_cmd + " 1> " + os.path.join(pipeline.lxd_logs_path, 'out.log') + " 2> " + os.path.join(pipeline.lxd_logs_path, "err.log\n")) #  || curl -X POST -d '{\"status\" : \"ERROR\"}' " + run.notify_url + "
            f.write("chown -Rf " + str(PIRUS_UID) + ":" + str(PIRUS_GID) + " " + pipeline.lxd_outputs_path + "\n")
            f.write("curl -X POST -d '{\"status\" : \"FINISHING\"}' " + run.notify_url + "\n")
            os.chmod(run_file, 0o777)

        # create container
        subprocess.call(["lxc", "init", run.lxd_image, run.lxd_container])
        # set up env
        subprocess.call(["lxc", "config", "set", run.lxd_container, "environment.PIRUS_NOTIFY_URL", self.notify_url ])
        subprocess.call(["lxc", "config", "set", run.lxd_container, "environment.PIRUS_CONFIG_FILE", os.path.join(pipeline.lxd_inputs_path, "config.json") ])
        # set up devices
        subprocess.call(["lxc", "config", "device", "add", run.lxd_container, "pirus_inputs",  "disk", "source="+inputs_path,   "path=" + pipeline.lxd_inputs_path[1:], "readonly=True"])
        subprocess.call(["lxc", "config", "device", "add", run.lxd_container, "pirus_outputs", "disk", "source="+outputs_path,  "path=" + pipeline.lxd_outputs_path[1:]])
        subprocess.call(["lxc", "config", "device", "add", run.lxd_container, "pirus_logs",    "disk", "source="+logs_path,     "path=" + pipeline.lxd_logs_path[1:]])
        subprocess.call(["lxc", "config", "device", "add", run.lxd_container, "pirus_db",      "disk", "source="+DATABASES_DIR, "path=" + pipeline.lxd_db_path[1:], "readonly=True"])
    except:
        return self.error('Unexpected error ' + str(sys.exc_info()[0]))
        raise 

    # Run the pipe !
    try:
        subprocess.call(["lxc", "start", run.lxd_container])
        lxd_run_file = os.path.join("/", os.path.basename(run_file))
        subprocess.call(["lxc", "file", "push", run_file, run.lxd_container + lxd_run_file])
        # for file_id in run.inputs:
        #     f = PirusFile.from_id(file_id)
        #     print ("push " + f.path + " to " + run.lxd_container + os.path.join(pipeline.lxd_inputs_path, f.name))
        #     subprocess.call(["lxc", "file", "push", f.path, run.lxd_container + os.path.join(pipeline.lxd_inputs_path, f.name)])
        subprocess.call(["lxc", "exec", run.lxd_container, "--",  "chmod", "+x", lxd_run_file])
        subprocess.Popen(["lxc", "exec", run.lxd_container, lxd_run_file])
        self.notify_status("RUNNING")
    except:
        return self.error('Unexpected error ' + str(sys.exc_info()[0])) 
        raise




@app.task(base=PirusTask, queue='PirusQueue', bind=True)
def terminate_run(self, run_id):
    # Init celery task
    from core.model import Run, PirusFile, Pipeline
    run = Run.from_id(run_id)
    if run is None :
        # TODO : log error
        return
    self.notify_url = run.notify_url


    # Register outputs files
    root_path    = os.path.join(RUNS_DIR, run.lxd_container)
    outputs_path = os.path.join(root_path, "outputs")
    logs_path    = os.path.join(root_path, "logs")

    run.end = str(datetime.datetime.now().timestamp())

    print("Analyse", outputs_path)
    run.outputs = []
    for f in os.listdir(outputs_path):
        if os.path.isfile(os.path.join(outputs_path, f)):
            file_name = str(uuid.uuid4())
            file_path = os.path.join(FILES_DIR, file_name)
            print (" - Move : ", f, " ==> ", file_path)
            # 1- move file to FILE directory
            shutil.copyfile(os.path.join(outputs_path, f), file_path)
            # 2- create link
            # os.link(file_path, os.path.join(outputs_path, f))

            # 3- register in db
            pirusfile = PirusFile()
            pirusfile.import_data({
                    "name"         : f,
                    "type"         : os.path.splitext(f)[1][1:].strip().lower(),
                    "path"         : file_path,
                    "size"         : os.path.getsize(file_path),
                    "upload_offset": os.path.getsize(file_path),
                    "status"       : "CHECKED",
                    "create_date"  : str(datetime.datetime.now().timestamp()),
                    "md5sum"       : self.hashfile(open(file_path, 'rb'), hashlib.md5()).hex(),
                    "runs"         : [ str(run.id) ],
                    "source"       : {"type" : "output", "run_id" : str(run.id), "run_name" : run.name}
                })
            pirusfile.save()
            run.outputs.append(str(pirusfile.id))

    # Stop container and clear resource
    try:
        # Clean outputs
        subprocess.call(["lxc", "exec", run.lxd_container, "--", "rm", ""])
        subprocess.call(["lxc", "delete", run.lxd_container, "--force"])
    except:
        return self.error('Unexpected error ' + str(sys.exc_info()[0]))
        raise


    
    run.save()
    self.notify_status("DONE")