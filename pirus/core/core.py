#!env/python3
# coding: utf-8
import ipdb

import os
import shutil
import json
import tarfile
import datetime
import time
import uuid
import subprocess
import requests



from config import *
from core.framework import *
from core.model import *
from core.container_managers.lxd_manager import LxdManager
from core.container_managers.github_manager import GithubManager
from core.queue_managers.sync_queue import PirusQueueManager

# need it, and only used by unittests.
from tests.core.fake_container_manager import FakeContainerManager4Test





# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# CORE OBJECT
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

def notify_all_print(msg):
    """
        Default delegate used by the core for notification.
    """
    print(str(msg))


class Core:
    def __init__(self):
        self.files = FileManager()
        self.pipelines = PipelineManager()
        self.jobs = JobManager()
        self.container_managers = {}

        # CHECK filesystem
        if not os.path.exists(JOBS_DIR):
            os.makedirs(JOBS_DIR)
        if not os.path.exists(PIPELINES_DIR):
            os.makedirs(PIPELINES_DIR)
        if not os.path.exists(FILES_DIR):
            os.makedirs(FILES_DIR)
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
        if not os.path.exists(DATABASES_DIR):
            os.makedirs(DATABASES_DIR)

        # Load Container managers
        self.container_managers["lxd"] = LxdManager()
        self.container_managers["github"] = GithubManager()

        # method handler to notify all
        # according to api that will be pluged on the core, this method should be overriden 
        # to really do a notification. (See how api_rest override this method)
        self.notify_all = notify_all_print

        # if TEST config
        self.container_managers["FakeManager4Test"] = FakeContainerManager4Test()


 

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# FILE MANAGER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class FileManager:
    def __init__(self):
        pass


    def upload_init(self, filename, file_size, metadata={}):
        """ 
            Create an entry for the file in the database and return the id of the file in pirus
            This method shall be used to init a resumable upload of a file 
            (the file is not yet available, but we can manipulate its pirus metadata)
        """
        pfile = File.new()
        pfile.name = filename
        pfile.type = os.path.splitext(filename)[1][1:].strip().lower()
        pfile.path = os.path.join(TEMP_DIR, str(uuid.uuid4()))
        pfile.size = int(file_size)
        pfile.upload_offset = 0
        pfile.status = "uploading"
        pfile.create_date = datetime.datetime.now()
        pfile.save()

        if metadata and len(metadata) > 0:
            pfile.load(metadata)
        log('PirusCore.FileManager.upload_init : New file registered with the id ' + str(pfile.id) + ' (available at ' + pfile.path + ')')
        return pfile



    def upload_chunk(self, file_id, file_offset, chunk_size, chunk):
        """
            Write chunk of data in the file uploading and update model
        """
        # Retrieve file
        pfile = File.from_id(file_id)
        if pfile == None:
            raise RegovarException("Unable to retrieve the pirus file with the provided id : " + file_id)

        # Write file chunk
        try:
            action = "br+" if os.path.lexists(pfile.path) else "bw"
            with open(pfile.path, action) as f:
                f.seek(file_offset)
                f.write(chunk)
        except IOError:
            raise RegovarException("Unable to write file chunk on the the server :(")

        # Update model
        pfile.upload_offset += chunk_size
        pfile.save()

        if pfile.upload_offset == pfile.size:
            self.upload_finish(file_id)

        return pfile



    def upload_finish(self, file_id, checksum=None, checksum_type="md5"):
        """ 
            When upload of a file is finish, we move it from the download temporary folder to the
            files folder. A checksum validation can also be done if provided. 
            Update finaly the status of the file to uploaded or checked -> file ready to be used
        """
        # Retrieve file
        global pirus
        pfile = File.from_id(file_id)
        if pfile == None:
            raise RegovarException("Unable to retrieve the pirus file with the provided id : " + file_id)
        # Move file
        old_path = pfile.path
        new_path = os.path.join(FILES_DIR, str(uuid.uuid4()))
        os.rename(old_path, new_path)
        # If checksum provided, check that file is correct
        file_status = "uploaded"
        if checksum is not None:
            if checksum_type == "md5" and md5(fullpath) != checksum : 
                raise error
            file_status = "checked"            
        # Update file data in database
        pfile.upload_offset = pfile.size
        pfile.status = file_status
        pfile.path = new_path
        pfile.save()

        # Check if the file is an image of a Pipeline. if true, automatically start the install
        pipeline = session().query(Pipeline).filter_by(image_file_id=pfile.id).first()
        if pipeline:
            pirus.pipelines.install(pipeline.id, pipeline.type)



    async def from_url(self, url, metadata={}):
        """ 
            Download a file from url and create a new Pirus file. 
            TODO : implementation have to be fixed
        """
        name = str(uuid.uuid4())
        filepath = os.path.join(FILES_DIR, name)
        # get request and write file
        with open(filepath, "bw+") as file:
            try :
                response = await requests.get(url)
            except Exception as err:
                raise RegovarException("Error occured when trying to download a file from the provided url : " + str(url), "", err)
            file.write(response.content)
        # save file on the database
        pirusfile = pirus.files.register(name, filepath, metadata)
        return rest_success(pirusfile)




    def from_local(self, path, move=False, metadata={}):
        """ 
            Copy or move a local file on server and create a new Pirus file. Of course the source file shall have good access rights. 
            TODO : implementation have to be fixed
        """
        if not os.path.isfile(path):
            raise RegovarException("File \"{}\" doesn't exists.".format(path))
        pfile = File.new()
        pfile.name = os.path.basename(path)
        pfile.type = os.path.splitext(pfile.name)[1][1:].strip().lower()
        pfile.path = os.path.join(FILES_DIR, str(uuid.uuid4()))
        pfile.size = os.path.getsize(path)
        pfile.upload_offset = 0
        pfile.status = "uploading"
        pfile.create_date = datetime.datetime.now()
        pfile.save()
        try:
            # Move file
            if move:
                os.rename(path, pfile.path)
            else:
                shutil.copyfile(path, pfile.path)
            # Update file data in database
            pfile.upload_offset = pfile.size
            pfile.status = "checked"
            pfile.save()
        except Exception as err:
            raise RegovarException("Error occured when trying to copy/move the file from the provided path : ".format(path), "", err)
        return pfile




    def delete(self, file_id):
        pfile = File.from_id(file_id)
        if pfile and os.path.isfile(pfile.path):
            os.remove(pfile.path)
            File.delete(file_id)


        








# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# PIPELINE MANAGER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class PipelineManager:
    def __init__(self):
        pass


    def install_init (self, name, metadata={}):
        pipe = Pipeline.new()
        pipe.name = name
        pipe.status = "initializing"
        pipe.save()

        if metadata and len(metadata) > 0:
            pipe.load(metadata)
        log('core.PipeManager.register : New pipe registered with the id {}'.format(pipe.id))
        return pipe



    def install_init_image_upload(self, filepath, file_size, metadata={}):
        """ 
            Initialise a pipeline installation. 
            To use if the image have to be uploaded on the server.
            Create an entry for the pipeline and the file (image that will be uploaded) in the database.
            Return the Pipeline and the File objects created

            This method shall be used to init a resumable upload of a pipeline 
            (the pipeline/image are not yet installed and available, but we need to manipulate them)
        """
        global pirus
        pfile = pirus.files.upload_init(filepath, file_size, metadata)
        pipe = self.install_init(filepath, metadata)
        pipe.image_file_id = pfile.id
        pipe.save()
        return pipe, pfile



    async def install_init_image_url(self, url, metadata={}):
        """ 
            Initialise a pipeline installation. 
            To use if the image have to be retrieved via an url.
            Create an entry for the pipeline and the file (image) in the database.
            Async method as the download start immediatly, followed by the installation when it's done

            Return the Pipeline object ready to be used
        """
        raise NotImplementedError("TODO")



    def install_init_image_local(self, filepath, move=False, metadata={}):
        """ 
            Initialise a pipeline installation. 
            To use if the image have to be retrieved on the local server.
            Create an entry for the pipeline and the file (image) in the database.
            Copy the local file into dedicated Pirus directory and start the installation of the Pipeline

            Return the Pipeline object ready to be used
        """
        global pirus
        pfile = pirus.files.from_local(filepath, move, metadata)
        pipe = self.install_init(filepath, metadata)

        # FIXME : Getting error 'is not bound to a Session' 
        #         why it occure here ... need to check that
        check_session(pfile)
        check_session(pipe)

        pipe.image_file_id = pfile.id
        pipe.save()
        return pipe




    def install(self, pipeline_id, pipeline_type=None):
        """
            Start the installation of the pipeline. (done in another thread)
            The initialization shall be done (image ready to be used), 
            Except for 'github' pipeline's type which don't need image (manager.need_image_file set to False)
        """
        global pirus

        pipeline = Pipeline.from_id(pipeline_id, 1)
        if not pipeline : 
            raise RegovarException("Pipeline not found (id={}).".format(pipeline_id))
        if pipeline.status != "initializing":
            raise RegovarException("Pipeline status ({}) is not \"initializing\". Cannot perform an installation.".format(pipeline.status))
        if pipeline.image_file and pipeline.image_file.status not in ["uploaded", "checked"]:
            raise RegovarException("Pipeline image (status={}) upload is not complete.".format(pipeline.image_file.status))

        if not pipeline.type: pipeline.type = pipeline_type
        if not pipeline.type :
            raise RegovarException("Pipeline type not set. Unable to know which kind of installation shall be performed.")
        if pipeline.type not in pirus.container_managers.keys():
            raise RegovarException("Unknow pipeline's type ({}). Installation cannot be performed.".format(pipeline.type))
        if pirus.container_managers[pipeline.type].need_image_file and not pipeline.image_file:
            raise RegovarException("This kind of pipeline need a valid image file to be uploaded on the server.")

        run_async(self.__install, pipeline)



    def __install(self, pipeline):
        try:
            result = pirus.container_managers[pipeline.type].install_pipeline(pipeline)
        except Exception as err:
            raise RegovarException("Error occured during installation of the pipeline. Installation aborded.", "", err)
        pipeline.status = "ready" if result else "error"
        pipeline.save()







    def delete(self, pipeline):
        """
            Start the uninstallation of the pipeline. (done in another thread)
            Remove image file if exists.
        """
        global pirus
        try:
            if pipeline:
                run_async(self.__delete, pipeline)                                     # Clean container
                if pipeline.image_file_id: pirus.files.delete(pipeline.image_file_id)  # Clean filesystem
                Pipeline.delete(pipeline.id)                                           # Clean DB
        except Exception as err:
            # TODO : manage error
            raise RegovarException("core.PipelineManager.delete : Unable to delete the pipeline with id " + str(pipeline.id), err)
            return False
        return True


    def __delete(self, pipeline):
        try:
            pirus.container_managers[pipeline.type].uninstall_pipeline(pipeline)
        except Exception as err:
            raise RegovarException("Error occured during uninstallation of the pipeline. Uninstallation aborded.", err)









# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Job MANAGER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 


class MonitoringLog:
    """
        Class to wrap log file and provide usefull related information and method to parse logs
    """
    def __init__(self, path):
        self.path = path
        self.name = path
        self.size = os.path.getsize(path)
        self.creation = datetime.datetime.fromtimestamp(os.path.getctime(path))
        self.update = datetime.datetime.fromtimestamp(os.path.getmtime(path))


    def tail(lines_number):
        """
            Return the N last lines of the log
        """
        try: 
            out_tail = subprocess.check_output(["tail", path, "-n", "100"]).decode()
        except Exception as error:
            out_tail = "No stdout log of the run."

        
    def head(lines_number):
        """
            Return the N first lines of the log
        """
        try: 
            err_tail = subprocess.check_output(["tail", path, "-n", "100"]).decode()
        except Exception as error:
            err_tail = "No stderr log of the run."


    def snip(from_line, to_line):
        """
            Return a snippet of the log, from the line N to the line N2
        """
        # TODO
        pass







class JobManager:
    def __init__(self):
        pass



    def set_status(self, job, new_status, notify=True):
        global  pirus
        # Avoid useless notification
        # Impossible to change state of a job in error or canceled
        if (new_status != "running" and job.status == new_status) or job.status in  ["error", "canceled"]:
            return
        # Update status
        job.status = new_status
        job.save()

        # Need to do something according to the new status ?
        # Nothing to do for status : "waiting", "initializing", "running", "finalizing"
        if job.status in ["pause", "error", "done", "canceled"]:
            s = session()
            next_jobs = s.query(Job).filter_by(status="waiting").order_by("priority").all()
            if len(next_jobs) > 0:
                # start_run.delay(str(next_jobs[0].id))
               PirusQueueManager.start_job(next_jobs[0].id)
        elif job.status == "finalizing":
            # terminate_run.delay(str(job.id))
            PirusQueueManager.terminate_job(job.id)
        # Push notification
        if notify:
            pirus.notify_all({"action": "job_updated", "data" : [job.to_json()]})






    def new(self, pipeline_id, config, inputs_ids=[]):
        """
            Create a new job for the specified pipepline (pipeline_id), with provided config and input's files ids
        """
        pipeline = Pipeline.from_id(pipeline_id)
        if not pipeline : 
            raise RegovarException("Pipeline not found (id={}).".format(pipeline_id))
        if pipeline.status != "ready":
            raise RegovarException("Pipeline status ({}) is not \"ready\". Cannot create a job.".format(pipeline.status))
        if not isinstance(config, dict) and "name" not in config.keys():
            raise RegovarException("A name must be provided to create new job")
        # Init model
        job = Job.new()
        job.status = "initializing"
        job.inputs_ids = inputs_ids
        job.name = config["name"]
        job.config = json.dumps(config)
        job.progress_value = 0
        job.pipeline_id = pipeline_id
        job.progress_label = "0%"
        job.save()
        job.init(1)
        # Init directories entries for the container
        root_path = os.path.join(JOBS_DIR, "{}_{}".format(job.pipeline_id, job.id))
        inputs_path = os.path.join(root_path, "inputs")
        outputs_path = os.path.join(root_path, "outputs")
        logs_path = os.path.join(root_path, "logs")
        if not os.path.exists(inputs_path): 
            os.makedirs(inputs_path)
        if not os.path.exists(outputs_path):
            os.makedirs(outputs_path)
            os.chmod(outputs_path, 0o777)
        if not os.path.exists(logs_path):
            os.makedirs(logs_path)
            os.chmod(logs_path, 0o777)
        # Put inputs files and job's config in the inputs directory of the job
        config_path = os.path.join(inputs_path, "config.json")
        with open(config_path, 'w') as f:
            f.write(json.dumps(job.config, sort_keys=True, indent=4))
            os.chmod(config_path, 0o777)
        for f in job.inputs:
            link_path = os.path.join(inputs_path, f.name)
            os.link(f.path, link_path)
            os.chmod(link_path, 0o644)

        # Call init of the container
        PirusQueueManager.init_job(job.id)

        # Return job object
        return job



    def start(self, job_id):
        """
            Start or restart the job
        """
        job = Job.from_id(job_id)
        if not job:
            raise RegovarException("Job not found (id={}).".format(job_id))
        if job.status not in ["waiting", "pause"]:
            raise RegovarException("Job status ({}) is not \"pause\" or \"waiting\". Cannot start the job.".format(job.status))
        # Call start of the container
        PirusQueueManager.start_job(job.id)


    def monitoring(self, job_id):
        """
            Retrieve monitoring information about the job.
            Return a Job object with a new attribute:
             - logs : list of MonitoringLog (log file) write by the run/manager in the run's logs directory
        """
        job = Job.from_id(job_id)
        if not job:
            raise RegovarException("Job not found (id={}).".format(job_id))
        if job.status == "initializing":
            raise RegovarException("Job status is \"initializing\". Cannot retrieve yet monitoring informations.")
        # Ask container manager to update data about container
        PirusQueueManager.monitoring_job(job.id)
        job_logs_path = os.path.join(JOBS_DIR, "{}_{}".format(job.pipeline_id, job.id), "logs")
        job.logs = [MonitoringLog(os.path.join(job_logs_path, logname)) for logname in os.listdir(job_logs_path) if os.path.isfile(os.path.join(job_logs_path, logname))]




    def pause(self, job_id):
        """
            Pause the job
            Return False if job cannot be pause; True otherwise
        """
        global pirus
        job = Job.from_id(job_id, 1)
        if not job:
            raise RegovarException("Job not found (id={}).".format(job_id))
        if not job.pipeline:
            raise RegovarException("No Pipeline associated to this job.")
        if not job.pipeline.type:
            raise RegovarException("Type of pipeline for this job is not set.")
        if job.pipeline.type not in pirus.container_managers.keys():
            raise RegovarException("Pipeline type of this job is not managed.")
        if not pirus.container_managers[job.pipeline.type].supported_features["pause_job"]:
            return False
        # Call pause of the container
        PirusQueueManager.pause_job(job.id)



    def stop(self, job_id):
        """
            Stop the job
        """
        job = Job.from_id(job_id)
        if not job:
            raise RegovarException("Job not found (id={}).".format(job_id))
        if job.status in ["error", "canceled", "done"]:
            raise RegovarException("Job status is \"{}\". Cannot stop the job.".format(job.status))
        # Call stop of the container
        PirusQueueManager.stop_job(job.id)


    def finalize(self, job_id):
        """
            Shall be called by the job itself when ending.
            save outputs files and ask the container manager to delete container
        """
        global pirus
        job = Job.from_id(job_id)
        if not job:
            raise RegovarException("Job not found (id={}).".format(job_id))
        # Register outputs files
        root_path = os.path.join(JOBS_DIR, "{}_{}".format(job.pipeline_id, job.id))
        inputs_path = os.path.join(root_path, "inputs")
        outputs_path = os.path.join(root_path, "outputs")
        logs_path = os.path.join(root_path, "logs")

        for f in os.listdir(outputs_path):
            file_path = os.path.join(outputs_path, f)
            if os.path.isfile(file_path):
                # 1- Move & store file into Pirus DB/Filesystem
                pf = pirus.files.from_local(file_path, True, {"job_source_id" : job.id})
                # 2- create link (to help admins when browsing pirus filesystem)
                os.link(pf.path, file_path)
                # 3- update job's entry in db to link file to job's outputs
                job.outputs_ids.append(pf.id)
        job.save()
        # Stop container and delete it
        PirusQueueManager.finalize_job(job.id)




    def delete(self, job_id):
        """
            Delete a Job. Outputs that have not yet been saved in Pirus, will be deleted.
        """
        job = Job.from_id(job_id)
        if not job:
            raise RegovarException("Job not found (id={}).".format(job_id))
        if job.status not in ["error", "canceled", "done"]:
            raise RegovarException("Job status is \"{}\". Cannot stop the job.".format(job.status))
        # Security, force call stop/delete the container
        PirusQueueManager.finalize_job(job.id)
        # Deleting file in the filesystem
        root_path = os.path.join(JOBS_DIR, "{}_{}".format(job.pipeline_id, job.id))
        shutil.rmtree(root_path, True)









# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# INIT OBJECTS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 



# Pirus core
pirus = Core()

# Pirus Queue Manager
PirusQueueManager.pirus = pirus