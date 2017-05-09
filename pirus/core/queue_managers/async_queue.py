#!env/python3
# coding: utf-8 

import multiprocessing

import ipdb


def enqueue(target, args):
    p = multiprocessing.Process(target, args)
    p.start()




def celery_init_job(job_id):
    """
        Call manager to prepare the container for the job.
    """
    from core.model import Job
    from core.core import pirus
    ipdb.set_trace()

    job = Job.from_id(job_id, 1)
    if job and job.status == "initializing":
        try:
            success = pirus.container_managers[job.pipeline.type].init_job(job)
        except Exception as err:
            # Log error
            pirus.jobs.set_status(job, "error")
            return
        pirus.jobs.set_status(job, "waiting" if success else "error")




def celery_start_job(job_id):
    """
        Call the container manager to start or restart the execution of the job.
    """
    from core.model import Job, File, Pipeline
    from core.core import pirus

    # Check that job exists
    job = Job.from_id(job_id, 1)
    if not job :
        # TODO : log error
        return 1

    # Ok, job is now waiting
    pirus.jobs.set_status(job, "waiting")

    # Check that all inputs files are ready to be used
    for file in job.inputs:
        if file is None :
            print('Inputs file deleted before the start of the run. Run aborded.')
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

    


def celery_monitoring_job(job_id):
    """
        Call manager to retrieve monitoring informations.
    """
    from core.model import Job
    from core.core import pirus

    job = Job.from_id(job_id, 1)
    if job and job.status == "initializing":
        try:
            pirus.container_managers[job.pipeline.type].init_job(job)
        except Exception as err:
            # Log error
            pirus.jobs.set_status(job, "error")
            return
        pirus.jobs.set_status(job, "waiting")



def celery_pause_job(job_id):
    """
        Call manager to suspend the execution of the job.
    """
    from core.model import Job
    from core.core import pirus

    job = Job.from_id(job_id, 1)
    if job and job.status == "initializing":
        try:
            pirus.container_managers[job.pipeline.type].init_job(job)
        except Exception as err:
            # Log error
            pirus.jobs.set_status(job, "error")
            return
        pirus.jobs.set_status(job, "waiting")




def celery_stop_job(job_id):
    """
        Call manager to stop execution of the job.
    """
    from core.model import Job
    from core.core import pirus

    job = Job.from_id(job_id, 1)
    if job and job.status == "initializing":
        try:
            pirus.container_managers[job.pipeline.type].init_job(job)
        except Exception as err:
            # Log error
            pirus.jobs.set_status(job, "error")
            return
        pirus.jobs.set_status(job, "waiting")




def celery_terminate_job(job_id):
    """
        Ask the manager to clear the container, and according to the status of the job :
         - "done" : moving and saving outputs files in Pirus
         - "error", "canceled" : keep outputs file in the job folder to allow debugging 
    """
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




def celery_delete_job(job_id):
    """
        Delete a job
        Call manager to prepare the container for the job.
    """
    from core.model import Job
    from core.core import pirus
    # By security : stop and terminate it first
    job = Job.from_id(job_id, 1)
    if job and job.status == "initializing":
        try:
            pirus.container_managers[job.pipeline.type].init_job(job)
        except Exception as err:
            # Log error
            pirus.jobs.set_status(job, "error")
            return
        pirus.jobs.set_status(job, "waiting")