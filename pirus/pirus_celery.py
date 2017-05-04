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
def start_job(self, run_id):
    from core.model import Job, File, Pipeline
    from core.core import pirus

    # Check that job exists
    job = Job.from_id(job_id, 1)
    if not job :
        # TODO : log error
        return 1

    # Ok, job is now waiting
    pirus.jobs.set_status("waiting")

    # Check that all inputs files are ready to be used
    for file in job.inputs:
        if file is None :
            return self.error('Inputs file deleted before the start of the run. Run aborded.')
        if file.status not in ["checked", "uploaded"]:
            # inputs not ready, we keep the run in the waiting status
            print("INPUTS of the run not ready. waiting")
            return 1
        
    # TODO : check that enough reszources to run the job
    # Inputs files ready to use, looking for lxd resources now
    # count = 0
    # for lxd_container in lxd_client.containers.all():
    #     if lxd_container.name.startswith(LXD_CONTAINER_PREFIX) and lxd_container.status == 'Running':
    #         count += 1
    # count = len(Run.objects(status="RUNNING")) + len(Run.objects(status="INITIALIZING")) + len(Run.objects(status="FINISHING"))
    # if len(Run.objects(status="RUNNING")) >= LXD_MAX:
    #     # too many run in progress, we keep the run in the waiting status
    #     print("To many run in progress, we keep the run in the waiting status")
    #     return 1

    #Try to run the job
    if pirus.container_managers[job.pipeline.type].start_job(job):
        pirus.jobs.set_status(job, "running")
        return 0
    else:
        return 1

    




@app.task(base=PirusTask, queue='PirusQueue', bind=True)
def terminate_job(self, job_id):
    from core.model import Job, File, Pipeline
    from core.core import pirus

    # Check that job exists
    job = Job.from_id(job_id, 1)
    if not job :
        # TODO : log error
        return 1

    if pirus.container_managers[job.pipeline.type].terminate_job(job):
        pirus.jobs.set_status(job, "done")
        return 0
    else:
        pirus.jobs.set_status(job, "error")
        return 1