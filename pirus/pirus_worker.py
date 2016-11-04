#!env/python3
# coding: utf-8 
import ipdb; 

import os
import sys
import time
import requests
import logging
import json
import pylxd
import subprocess
import shutil
import uuid

from mongoengine import *
from celery import Celery, Task
from config import *
from framework import *






app = Celery('pirus_worker')
app.conf.update(
    BROKER_URL = 'amqp://guest@localhost',
    CELERY_RESULT_BACKEND = 'rpc',
    CELERY_RESULT_PERSISTENT = False,

    CELERY_TASK_SERIALIZER = 'json',
    CELERY_ACCEPT_CONTENT = ['json'],
    CELERY_RESULT_SERIALIZER = 'json',
    CELERY_INCLUDE = [
    'pirus_worker'
    ],
    CELERY_TIMEZONE = 'Europe/Paris',
    CELERY_ENABLE_UTC = True,
)


lxd_client = pylxd.Client()









def execute(cmd, olog=None, elog=None):
    subprocess.call(cmd)
    # with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
    #     # TODO FIXME => logging realtime not working :( ...
    #     out = str(proc.stdout.read())
    #     err = str(proc.stderr.read())
    #     if out != "":
    #         olog.info(out)
    #     if err != "":
    #         elog.info(err)



class PirusTask(Task):
    """Task that sends notification on completion."""
    abstract = True

    notify_url = ""
    run_path   = ""

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        #data = {'clientid': kwargs['clientid'], 'result': retval}
        #requests.get(NOTIFY_URL, data=data)
        pass

    def dump_context(self):
        print('  Context : Executing task id {0.id}, args: {0.args!r} kwargs: {0.kwargs!r}'.format(self.request))


    def notify_status(self, status:str):
        requests.post(self.notify_url, data = '{"status": "'+status+'"}' )

    def error(self, msg:str, error_code:int=500):
        # TODO : some log ?...
        self.notify_status('ERROR')
        return error_code







@app.task(base=PirusTask, queue='PirusQueue', bind=True)
def run_pipeline(self, run_id):
    from api_v1.model import Run, PirusFile, Pipeline
    connect('pirus')

    run = Run.from_id(run_id)
    if run is None :
        # TODO : log error
        return

    self.notify_url = run.notify_url()
    # # Init logs
    # print(os.path.join(lpath, "pirus.log"))
    # setup_logger('pirus_worker', os.path.join(lpath, "pirus_worker.log"))
    # setup_logger('run_out', os.path.join(lpath, "out.log"))
    # setup_logger('run_err', os.path.join(lpath, "err.log"))
    # wlog = logging.getLogger('pirus_worker')
    # # olog = logging.getLogger('run_out')
    # # elog = logging.getLogger('run_err')
    
    # wlog.info('INIT    | Pirus worker initialisation : ')
    # wlog.info('INIT    |  - LXD alias : ' + pipeline.lxd_alias)
    # wlog.info('INIT    |  - Run ID  : ' + self.run_private_id)
    # wlog.info('INIT    | Directory created : ')
    # wlog.info('INIT    |  - inputs  : ' + ipath)
    # wlog.info('INIT    |  - outputs : ' + opath)
    # wlog.info('INIT    |  - logs    : ' + lpath)
    # wlog.info('INIT    |  - db      : ' + DATABASES_DIR)
    # wlog.info('INIT    | Run config : ' + json.dumps(config))
    # wlog.info('INIT    | Run inputs : ' + json.dumps(inputs))



    run.status = "WAITING"
    run.save()

    # Check that all inputs files are ready to be used
    for file_id in run.inputs:
        f = PirusFile.from_id(file_id)
        if f is None :
            return self.error('Inputs file deleted before the start of the run. Run aborded.')
        if f.status not in ["CHECKED", "UPLOADED"]:
            # inputs not ready, we keep the run in the waiting status
            return 1
        
    # Inputs files ready to use, looking for lxd resources now
    count = 0
    for lxd_container in lxd_client.containers.all():
        if lxd_container.name.startswith(LXD_PREFIX) and lxd_container.status == 'Running':
            count += 1
    if count >= LXD_MAX:
        # too many run in progress, we keep the run in the waiting status
        return 1


    #LXD ready ! Prepare filesystem of the server to host lxc container files
    root_path    = os.path.join(RUNS_DIR, self.run_private_id)
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
    with open(conf_file, 'w') as f:
        ipdb.set_trace()
        f.write(json.dumps(run.config))
        os.chmod(conf_file, 0o777)

    for file_id in run.inputs:
        f = PirusFile.from_id(file_id)
        os.symlink(f.file_path, os.path.join(inputs_path, f.file_name))

    # Setting up the lxc container for the run
    wlog.info('SETUP   | Creation of the LXC container from image "' + run.lxd_image + '"')

    self.notify_status("INITIALIZING")
    try:
        pipeline = Pipeline.from_id(run.pipeline_id)
        # create container
        subprocess.call(["lxc", "init", run.lxd_image, run.lxd_container])
        # set up env
        subprocess.call(["lxc", "config", "set", run.lxd_container, "environment.PIRUS_NOTIFY_URL", self.notify_url ])
        # set up devices
        subprocess.call(["lxc", "config", "device", "add", run.lxd_container, "pirus_inputs",  "disk", "source="+inputs_path,   "path=" + pipeline.lxd_inputs_path[1:], "readonly=True"])
        subprocess.call(["lxc", "config", "device", "add", run.lxd_container, "pirus_outputs", "disk", "source="+outputs_path,  "path=" + pipeline.lxd_outputs_path[1:]])
        subprocess.call(["lxc", "config", "device", "add", run.lxd_container, "pirus_logs",    "disk", "source="+logs_path,     "path=" + pipeline.lxd_logs_path[1:]])
        subprocess.call(["lxc", "config", "device", "add", run.lxd_container, "pirus_db",      "disk", "source="+DATABASES_DIR, "path=" + pipeline.lxd_db_path[1:], "readonly=True"])
    except:
        wlog.info('ERROR   | Unexpected error ' + str(sys.exc_info()[0]))
        self.notify_status("ERROR")
        raise

    # Run the pipe !
    wlog.info('RUN     | Run the pipe !')
    self.notify_status("RUN")
    try:
        subprocess.call(["lxc", "start", run.lxd_container])
        # subprocess.call(["echo", '"/pipeline/run/run.sh > /pipeline/logs/out.log 2> /pipeline/logs/err.log"',  ">", "/pipeline/run/runcontainer.sh"])
        # subprocess.call(["chmod", '+x',  ">", "/pipeline/run/runcontainer.sh"])
        subprocess.Popen(["lxc", "exec", run.lxd_container, pipeline.lxd_run_cmd], stdout=open(logs_path+"/out.log", "w"), stderr=open(logs_path+"/err.log", "w"))
    except:
        wlog.info('ERROR   | Unexpected error ' + str(sys.exc_info()[0]))
        self.notify_status("ERROR")
        raise




@app.task(base=PirusTask, queue='PirusQueue', bind=True)
def terminate_run(self, run_id):
    # Init celery task
    from api_v1.model import Run, PirusFile, Pipeline
    connect('pirus')
    run = Run.from_id(run_id)
    if run is None :
        # TODO : log error
        return
    self.notify_url = run.notify_url()


    # Stop container and clear resource
    wlog.info('STOP    | Run ending')
    self.notify_status("STOP")
    try:
        # Clean outputs
        wlog.info('STOP    |  - chmod 775 on outputs and logs files produced by the container')
        subprocess.call(["lxc", "exec", run.lxd_container, "--", "chmod", "755", "-Rf", "/pipeline"])

        wlog.info('STOP    |  - closing and deleting the lxc container : ' + run.lxd_container)
        subprocess.call(["lxc", "delete", run.lxd_container, "--force"])
    except:
        wlog.info('ERROR   | Unexpected error ' + str(sys.exc_info()[0]))
        self.notify_status("ERROR")
        raise

    # Register outputs files
    print("outputs check : ", opath)
    for f in os.listdir(opath):
        if os.path.isfile(f):
            print ("output to mv : ", f)
            file_name = str(uuid.uuid4())
            file_path = os.path.join(FILES_DIR, file_name)
            # 1- move file to FILE directory
            shutil.move(os.path.join(opath, f), file_path)
            # 2- create symlink
            os.symlink(file_path, os.path.join(opath, f))

            # 3- register in db
            pirusfile = PirusFile()
            pirusfile.import_data({
                    "file_name"    : f,
                    "file_type"    : os.path.splitext(f)[1][1:].strip().lower(),
                    "file_path"    : file_path,
                    "file_size"    : humansize(os.path.getsize(file_path)),
                    "status"       : "OK",
                    "create_date"  : str(datetime.datetime.now().timestamp()),
                    "md5sum"       : md5(file_path),
                    "tags"         : tags,
                    "comments"     : comments,
                    "runs"         : { str(run.id) : "out" }
                })
            pirusfile.save()


    
    # It's done :)
    self.notify_status("DONE")
    wlog.info('STOP    | All is done. Bye.')