#!env/python3
# coding: utf-8 


import ipdb

from core.model import Job




class PirusQueueManager:


    def enqueue(target, args):
        target(*args)




    def init_job(job_id):
        """
            Call manager to prepare the container for the job.
        """
        job = Job.from_id(job_id, 1)
        if job and job.status == "initializing":
            try:
                success = PirusQueueManager.pirus.container_managers[job.pipeline.type].init_job(job)
            except Exception as err:
                # Log error
                PirusQueueManager.pirus.jobs.set_status(job, "error")
                return
            PirusQueueManager.pirus.jobs.set_status(job, "waiting" if success else "error")




    def start_job(job_id):
        """
            Call the container manager to start or restart the execution of the job.
        """
        # Check that job exists
        job = Job.from_id(job_id, 1)
        if not job :
            # TODO : log error
            return 1

        # Ok, job is now waiting
        PirusQueueManager.pirus.jobs.set_status(job, "waiting")

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
        if PirusQueueManager.pirus.container_managers[job.pipeline.type].start_job(job):
            PirusQueueManager.pirus.jobs.set_status(job, "running")
            return 0
        else:
            return 1

        


    def monitoring_job(job_id):
        """
            Call manager to retrieve monitoring informations.
        """
        job = Job.from_id(job_id, 1)
        if job:
            try:
                PirusQueueManager.pirus.container_managers[job.pipeline.type].monitoring_job(job)
            except Exception as err:
                # Log error
                PirusQueueManager.pirus.jobs.set_status(job, "error")
                return
            PirusQueueManager.pirus.jobs.set_status(job, "waiting")



    def pause_job(job_id):
        """
            Call manager to suspend the execution of the job.
        """
        job = Job.from_id(job_id, 1)
        if job:
            try:
                PirusQueueManager.pirus.container_managers[job.pipeline.type].pause_job(job)
            except Exception as err:
                # Log error
                PirusQueueManager.pirus.jobs.set_status(job, "error")
                return
            PirusQueueManager.pirus.jobs.set_status(job, "waiting")




    def stop_job(job_id):
        """
            Call manager to stop execution of the job.
        """
        job = Job.from_id(job_id, 1)
        if job:
            try:
                PirusQueueManager.pirus.container_managers[job.pipeline.type].stop_job(job)
            except Exception as err:
                # Log error
                PirusQueueManager.pirus.jobs.set_status(job, "error")
                return
            PirusQueueManager.pirus.jobs.set_status(job, "waiting")




    def finalize_job(job_id):
        """
            Ask the manager to clear the container
        """
        job = Job.from_id(job_id, 1)
        if not job :
            # TODO : log error
            return 1

        if PirusQueueManager.pirus.container_managers[job.pipeline.type].finalize_job(job):
            PirusQueueManager.pirus.jobs.set_status(job, "done")
            return 0
        else:
            PirusQueueManager.pirus.jobs.set_status(job, "error")
            return 1




    def delete_job(job_id):
        """
            Delete a job
            Call manager to prepare the container for the job.
        """
        job = Job.from_id(job_id, 1)
        if job:
            try:
                PirusQueueManager.pirus.container_managers[job.pipeline.type].delete_job(job)
            except Exception as err:
                # Log error
                PirusQueueManager.pirus.jobs.set_status(job, "error")
                return
            PirusQueueManager.pirus.jobs.set_status(job, "waiting")