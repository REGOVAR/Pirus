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
        requests.post(self.notify_url, , data = {"status": status} )




@app.task(base=PirusTask, queue='PirusQueue', bind=True)
def run_pipeline(self, pipe_image_alias, config, inputs):
    from api_v1.model import Run, PirusFile


    self.run_celery_id = str(self.request.id)
    self.notify_url = 'http://' + HOSTNAME + '/run/notify/' + self.run_celery_id
    config["pirus"]["notify_url"] = self.notify_url

    # Init path
    rpath = os.path.join(RUNS_DIR, self.run_celery_id)
    ipath = os.path.join(rpath, "inputs")
    opath = os.path.join(rpath, "outputs")
    lpath = os.path.join(rpath, "logs")

    # Init directories
    if not os.path.exists(ipath):
        os.makedirs(ipath)
    if not os.path.exists(opath):
        os.makedirs(opath)
        os.chmod(opath, 0o777)
    if not os.path.exists(lpath):
        os.makedirs(lpath)
        os.chmod(lpath, 0o777)

    # Init logs
    print(os.path.join(lpath, "pirus.log"))
    setup_logger('pirus_worker', os.path.join(lpath, "pirus_worker.log"))
    setup_logger('run_out', os.path.join(lpath, "out.log"))
    setup_logger('run_err', os.path.join(lpath, "err.log"))
    wlog = logging.getLogger('pirus_worker')
    # olog = logging.getLogger('run_out')
    # elog = logging.getLogger('run_err')
    
    wlog.info('INIT    | Pirus worker initialisation : ')
    wlog.info('INIT    |  - LXD alias : ' + pipe_image_alias)
    wlog.info('INIT    |  - Run ID  : ' + self.run_celery_id)
    wlog.info('INIT    | Directory created : ')
    wlog.info('INIT    |  - inputs  : ' + ipath)
    wlog.info('INIT    |  - outputs : ' + opath)
    wlog.info('INIT    |  - logs    : ' + lpath)
    wlog.info('INIT    |  - db      : ' + DATABASES_DIR)
    wlog.info('INIT    | Run config : ' + json.dumps(config))
    wlog.info('INIT    | Run inputs : ' + json.dumps(inputs))



    # Init inputs
    cfile = os.path.join(ipath, "config.json")
    with open(cfile, 'w') as f:
        f.write(json.dumps(config))
        os.chmod(cfile, 0o777)

    for ifile in inputs:
        pirusfile = PirusFile.from_id(ifile[0])
        if pirusfile is None :
            pass
        else:
            os.symlink(PirusFile.file_path, os.path.join(ipath, ifile[1]))


    # Check database, to see how many container are running and if we can create a new one for this run
    wlog.info('WAITING | Looking for lxc container creation ...')
    self.notify_status("WAITING")
    try:
        while len(lxd_client.containers.all()) >= LXD_MAX:
            time.sleep(1)
        wlog.info('WAITING | ' + str(len(lxd_client.containers.all())) + '/' + str(LXD_MAX) + ' containers -> ok to create a new one')
        c_name = LXD_PREFIX + "-" + self.run_celery_id
    except:
        wlog.info('FAILLED | Unexpected error ' + str(sys.exc_info()[0]))
        self.notify_status("FAILLED")
        raise


    # Setting up the lxc container for the run
    wlog.info('SETUP   | Creation of the LXC container from image "' + pipe_image_alias + '"')
    self.notify_status("BUILDING")
    try:
        # create container
        execute(["lxc", "init", pipe_image_alias, c_name])
        # set up env
        execute(["lxc", "config", "set", c_name, "environment.NOTIFY", self.notify_url ])
        # set up devices
        execute(["lxc", "config", "device", "add", c_name, "pirus_inputs",  "disk", "source="+ipath,         "path=pipeline/inputs", "readonly=True"])
        execute(["lxc", "config", "device", "add", c_name, "pirus_outputs", "disk", "source="+opath,         "path=pipeline/outputs"])
        execute(["lxc", "config", "device", "add", c_name, "pirus_logs",    "disk", "source="+lpath,         "path=pipeline/logs"])
        execute(["lxc", "config", "device", "add", c_name, "pirus_db",      "disk", "source="+DATABASES_DIR, "path=pipeline/db",     "readonly=True"])
        # TODO => create symlink in ipath directory
        # TODO => copy config file of the run in the ipath directory
    except:
        wlog.info('FAILLED | Unexpected error ' + str(sys.exc_info()[0]))
        self.notify_status("FAILLED")
        raise

    # Run the pipe !
    wlog.info('RUN     | Run the pipe !')
    self.notify_status("RUN")
    try:
        execute(["lxc", "start", c_name])
        # execute(["echo", '"/pipeline/run/run.sh > /pipeline/logs/out.log 2> /pipeline/logs/err.log"',  ">", "/pipeline/run/runcontainer.sh"])
        # execute(["chmod", '+x',  ">", "/pipeline/run/runcontainer.sh"])
        res = subprocess.call(["lxc", "exec", c_name, "/pipeline/run/run.sh"], stdout=open(lpath+"/out.log", "w"), stderr=open(lpath+"/err.log", "w"))

    except:
        wlog.info('FAILLED | Unexpected error ' + str(sys.exc_info()[0]))
        self.notify_status("FAILLED")
        raise

    # Stop container and clear resource
    wlog.info('STOP    | Run ending')
    self.notify_status("STOP")
    try:
        # Clean outputs
        wlog.info('STOP    |  - chmod 775 on outputs and logs files produced by the container')
        execute(["lxc", "exec", c_name, "--", "chmod", "755", "-Rf", "/pipeline"])

        wlog.info('STOP    |  - closing and deleting the lxc container : ' + c_name)
        execute(["lxc", "delete", c_name, "--force"])
    except:
        wlog.info('FAILLED | Unexpected error ' + str(sys.exc_info()[0]))
        self.notify_status("FAILLED")
        raise
    
    # It's done :)
    self.notify_status("DONE")
    wlog.info('STOP    | All is done. Bye.')


@app.task(base=PirusTask, queue='PirusQueue', bind=True)
def start_run(self, run_id, config):
    pass


@app.task(base=PirusTask, queue='PirusQueue', bind=True)
def freeze_run(self, run_id):
    pass