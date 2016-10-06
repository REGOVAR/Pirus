#!env/python3
# coding: utf-8 

import os
import sys
import requests
import logging
import json
import pylxd
import subprocess

from celery import Celery, Task
from config import *






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







def setup_logger(logger_name, log_file, level=logging.INFO):
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)s | %(message)s')
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    l.setLevel(level)
    l.addHandler(fileHandler)
    l.addHandler(streamHandler)

def execute(cmd, olog, elog):
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        # TODO FIXME => logging realtime not working :( ...
        olog.info(proc.stdout.read())
        elog.info(proc.stderr.read())



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
        requests.get(self.notify_url + "/status/" + status)
        print ("send notify status : ", self.notify_url + "/status/" + status)




@app.task(base=PirusTask, queue='PirusQueue', bind=True)
def run_pipeline(self, pipe_image_alias, config):
    self.run_id = str(self.request.id)
    self.notify_url = NOTIFY_URL + str(self.request.id)

    # Init path
    rpath = os.path.join(RUNS_DIR, self.run_id)
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
    setup_logger('pirus_worker', os.path.join(lpath, "pirus.log"))
    setup_logger('run_out', os.path.join(lpath, "out.log"))
    setup_logger('run_err', os.path.join(lpath, "err.log"))
    plog = logging.getLogger('pirus_worker')
    olog = logging.getLogger('run_out')
    elog = logging.getLogger('run_err')
    
    plog.info('INIT    | Pirus worker initialisation : ')
    plog.info('INIT    |  - Pipe ID : ' + pipe_image_alias)
    plog.info('INIT    |  - Run ID  : ' + self.run_id)
    plog.info('INIT    | Directory created : ')
    plog.info('INIT    |  - inputs  : ' + ipath)
    plog.info('INIT    |  - outputs : ' + opath)
    plog.info('INIT    |  - logs    : ' + lpath)
    plog.info('INIT    |  - db      : ' + DATABASES_DIR)

    # Check database, to see how many container are running and if we can create a new one for this run
    plog.info('WAITING | Looking for lxc container creation ...')
    self.notify_status("WAITING")
    try:
        while len(lxd_client.containers.all()) >= LXD_MAX:
            time.sleep(1)
        plog.info('WAITING | ' + str(len(lxd_client.containers.all())) + '/' + str(LXD_MAX) + ' containers -> ok to create a new one')
        c_name = LXD_PREFIX + "-" + self.run_id
    except:
        plog.info('FAILLED | Unexpected error ' + sys.exc_info()[0])
        self.notify_status("FAILLED")
        raise


    # Setting up the lxc container for the run
    plog.info('SETUP   | Creation of the LXC container from image "' + pipe_image_alias + '"')
    self.notify_status("BUILDING")
    try:
        # create container
        execute(["lxc", "init", "PirusBasic", c_name], olog, elog)
        # set up env
        execute(["lxc", "config", "set", c_name, "environment.NOTIFY", 'http://' + HOSTNAME + '/run/notify/' + self.run_id + '/'], olog, elog)
        # set up devices
        execute(["lxc", "config", "device", "add", c_name, "pirus_inputs",  "disk", "source="+ipath,         "path=pipeline/inputs", "readonly=True"], olog, elog)
        execute(["lxc", "config", "device", "add", c_name, "pirus_outputs", "disk", "source="+opath,         "path=pipeline/outputs"], olog, elog)
        execute(["lxc", "config", "device", "add", c_name, "pirus_logs",    "disk", "source="+lpath,         "path=pipeline/logs"], olog, elog)
        execute(["lxc", "config", "device", "add", c_name, "pirus_db",      "disk", "source="+DATABASES_DIR, "path=pipeline/db",     "readonly=True"], olog, elog)
        # TODO => create symlink in ipath directory
        # TODO => copy config file of the run in the ipath directory
    except:
        plog.info('FAILLED | Unexpected error ' + sys.exc_info()[0])
        self.notify_status("FAILLED")
        raise

    # Run the pipe !
    plog.info('RUN     | Run the pipe !')
    self.notify_status("RUN")
    try:
        execute(["lxc", "start", c_name], olog, elog)
        execute(["lxc", "exec", c_name, "/pipeline/run/run.sh"], olog, elog)
    except:
        plog.info('FAILLED | Unexpected error ' + sys.exc_info()[0])
        self.notify_status("FAILLED")
        raise

    # Stop container and clear resource
    plog.info('STOP    | Run ending')
    self.notify_status("STOP")
    try:
        # Force the container to change results files owner to allow the server to use them
        plog.info('STOP    |  - chown ' +  str(os.getuid()) + ":" + str(os.getgid()) + ' on outputs and logs files produced by the container')
        execute(["lxc", "exec", c_name, "--", "chown", str(os.getuid()) + ":" + str(os.getgid()), "-Rf", "/pipeline"])

        plog.info('STOP    |  - chmod 775 on outputs and logs files produced by the container')
        execute(["lxc", "exec", c_name, "--", "chmode", "775", "-Rf", "/pipeline"])

        plog.info('STOP    |  - closing and deleting the lxc container : ' + c_name)
        execute(["lxc", "delete", c_name, "--force"], olog, elog)
    except:
        plog.info('FAILLED | Unexpected error ' + sys.exc_info()[0])
        self.notify_status("FAILLED")
        raise
    
    # It's done :)
    self.notify_status("DONE")
    plog.info('STOP    | All is done. Bye.')


