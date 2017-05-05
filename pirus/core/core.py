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
from core.managers.lxd_manager import LxdManager
from core.managers.github_manager import GithubManager
from pirus_celery import start_job, terminate_job






def notify_all_print(msg):
    print(msg)



# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# CORE OBJECT
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
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



 

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# FILE MANAGER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class FileManager:
    def __init__(self):
        pass


    def get(self, fields=None, query=None, order=None, offset=None, limit=None, sublvl=0):
        """
            Generic method to get files metadata according to provided filtering options
        """
        if fields is None:
            fields = File.public_fields
        if query is None:
            query = {}
        if order is None:
            order = ['-create_date', "name"]
        if offset is None:
            offset = 0
        if limit is None:
            limit = offset + RANGE_MAX
        return [f.export_client_data(sublvl, fields) for f in File.objects(__raw__=query).order_by(*order)[offset:limit]]




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
        rlog.info('PirusCore.FileManager.upload_init : New file registered with the id ' + str(pfile.id) + ' (available at ' + pfile.path + ')')
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

        # TODO : check if the file is an image of a Pipeline. if true, automatically start the install
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
        name = str(uuid.uuid4())
        filepath = os.path.join(FILES_DIR, name)
        # get request and write file
        try:
            if move:
                os.rename(path, filepath)
            else:
                shutil.copyfile(path, filepath)
        except Exception as err:
            raise RegovarException("Error occured when trying to copy/move the file from the provided path : " + str(path), "", err)
        # save file on the database
        pirusfile = pirus.files.register(name, filepath, metadata)
        return rest_success(pirusfile)




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



    def install_init_image_upload(self, filename, file_size, metadata={}):
        """ 
            Initialise a pipeline installation. 
            To use if the image have to be uploaded on the server.
            Create an entry for the pipeline and the file (image that will be uploaded) in the database.
            Return the Pipeline and the File objects created

            This method shall be used to init a resumable upload of a pipeline 
            (the pipeline/image are not yet installed and available, but we need to manipulate them)
        """
        global pirus
        pfile = pirus.files.upload_init(filename, file_size, metadata)
        pipe = Pipeline.new()
        pipe.name = filename
        pipe.status = "initializing"
        pipe.image_file_id = pfile.id
        pipe.save()

        if metadata and len(metadata) > 0:
            pipe.load(metadata)
        rlog.info('core.PipeManager.register : New pipe registered with the id {}'.format(pipe.id))
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



    def install_init_image_local(self, filepath, metadata={}):
        """ 
            Initialise a pipeline installation. 
            To use if the image have to be retrieved on the local server.
            Create an entry for the pipeline and the file (image) in the database.
            Copy the local file into dedicated Pirus directory and start the installation of the Pipeline

            Return the Pipeline object ready to be used
        """
        raise NotImplementedError("TODO")




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
            raise RegovarException("Error occured during installation of the pipeline. Installation aborded.", err)
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
class JobManager:
    def __init__(self):
        pass


        
    # def public_fields(self):
    #     return Job.public_fields


    # def total(self):
    #     return Job.objects.count()


    # def get_from_id(self, job_id, sublvl=0, fields=None):
    #     job = Job.from_id(job_id)
    #     if job == None:
    #         raise RegovarException("No job with id " + str(job_id))
    #     return job.export_client_data(sublvl, fields)


    # def get_from_ids(self, file_ids, sublvl=0, fields=None):
    #     return [r.export_client_data(sublvl, fields) for r in Job.from_id(file_ids)]


    # def get_io(self, job_id):
    #     job = Job.from_id(job_id)
    #     if job == None:
    #         return rest_error("Unable to find the job with id " + str(job_id))
    #     result={"inputs" : [], "outputs":[]}
    #     # Retrieve inputs files data of the job
    #     files = File.from_ids(job.inputs)
    #     result["inputs"] = [a.export_client_data() for a in files]
    #     # Retrieve outputs files data of the job
    #     files = File.from_ids(job.outputs)
    #     result["outputs"] = [a.export_client_data() for a in files]
    #     return result


    def get(self, fields=None, query=None, order=None, offset=None, limit=None, sublvl=0):
        """
            Generic method to get jobs metadata according to provided filtering options
        """
        if fields is None:
            fields = Job.public_fields
        if query is None:
            query = {}
        if order is None:
            order = ['-create_date', "name"]
        if offset is None:
            offset = 0
        if limit is None:
            limit = offset + RANGE_MAX
        return [r.export_client_data(sublvl, fields) for r in Job.objects(__raw__=query).order_by(*order)[offset:limit]]






    def delete(self, job_id):
        try:
            # Start by doing a stop if running
            result, job = self.stop(job_id)
            # Remove files entries
            root_path    = os.path.join(JOBS_DIR, job.lxd_container)
            shutil.rmtree(root_path, True)
            # Clean DB
            job.delete()
        except Exception as err:
            raise RegovarException("core.JobManager.delete : Unable to delete the job with id " + str(job_id), "", err)
        return True



    def create(self, pipeline_id, config_data, inputs_data):
        config_data = { "job" : config_data, "pirus" : { "notify_url" : ""}}
        pipeline = Pipeline.from_id(pipeline_id)
        if pipeline is None:
            # TODO : LOG rest_error("Unknow pipeline id " + str(pipeline_id))
            return None
        # Create job in database.
        lxd_container = LXD_CONTAINER_PREFIX + str(uuid.uuid4())
        job = Job()
        job.import_data({
            "pipeline_id" : pipeline_id,
            "name" : config_data["job"]["name"],
            "lxd_container" : lxd_container,
            "lxd_image" : pipeline.lxd_alias,
            "start" : str(datetime.datetime.now().timestamp()),
            "status" : "WAITING",
            "config" : json.dumps(config_data),
            "inputs" : inputs_data,
            "progress" : {"value" : 0, "label" : "0%", "message" : "", "min" : 0, "max" : 0}
        })
        job.save()

        job.url = 'http://' + HOST_P + '/dl/r/' + str(job.id)
        job.notify_url = 'http://' + HOST_P + '/job/notify/' + str(job.id)
        config_data = json.loads(job.config)
        config_data["pirus"]["notify_url"] = job.notify_url
        job.config = json.dumps(config_data)

        # Update input files to indicate that they will be used by this job
        for file_id in job.inputs:
            f = File.from_id(file_id)
            if f is None :
                # This file doesn't exists, so we will ignore it
                job.inputs.remove(file_id)
            elif job.id not in f.jobs :
                f.jobs.append(str(job.id))
                f.save()
        
        job.save()

        return job.export_client_data()







    def update(self, job_id, json_data):
        job = Job.from_id(job_id)
        if job is not None:
            # special management when status change
            if "status" in json_data.keys() :
                self.set_status(job, json_data["status"], False)
            job.import_data(json_data)
            job.save()
            # send notification only when realy needed
            if "status" in json_data.keys() or "progress" in json_data.keys():
                msg = {"action":"job_changed", "data" : [job.export_client_data()] }
                pirus.notify_all(json.dumps(msg))
        return job


    # Update the status of the job, and according to the new status will do specific action
    # Notify also every one via websocket that job status changed
    def set_status(self, job, new_status, notify=True):
        global  pirus
        # Avoid useless notification
        # Impossible to change state of a job in error or canceled
        if (new_status != "RUNNING" and job.status == new_status) or job.status in  ["ERROR", "CANCELED"]:
            return
        # Update status
        job.status = new_status
        job.save()

        # Need to do something according to the new status ?
        # Nothing to do for status : "WAITING", "INITIALIZING", "RUNNING", "FINISHING"
        if job.status in ["PAUSE", "ERROR", "DONE", "CANCELED"]:
            next_job = Job.objects(status="WAITING").order_by('start')
            if len(next_job) > 0:
                if next_job[0].status == "PAUSE":
                    start_job.delay(str(next_job[0].id))
                else :
                    start_job.delay(str(next_job[0].id))
        elif job.status == "FINISHING":
            terminate_job.delay(str(job.id))
        # Push notification
        if notify:
            msg = {"action":"job_changed", "data" : [job.export_client_data()] }
            pirus.notify_all(json.dumps(msg))



    def start(self, job_id):
        job = Job.from_id(job_id)
        if job == None:
            raise RegovarException("Unable to find the job with id " + str(job_id))
        start_job.delay(job_id)


    def pause(self, job_id):
        global pirus
        job = Job.from_id(job_id, 1)
        if pirus.container_managers[job.pipeline.type].pause_job(job):
            self.set_status(job, "pause")







    def stop(self, job_id):
        job = Job.from_id(job_id)
        if job == None:
            raise RegovarException("Unable to find the job with id " + str(job_id))
        if job.status in ["WAITING", "PAUSE", "INITIALIZING", "RUNNING", "FINISHING"]:
            subprocess.Popen(["lxc", "delete", job.lxd_container, "--force"])
            self.set_status(job, "CANCELED")
            return True, job
        return False, job


    def monitoring(self, job_id):
        job = Job.from_id(job_id)
        if job == None:
            raise RegovarException("Unable to find the job with id " + str(job_id))

        pipeline = Pipeline.from_id(job.pipeline_id)
        # Result
        result = {
            "name" : job.name,
            "pipeline_icon" : pipeline.icon_url,
            "pipeline_name" : pipeline.name,
            "id" : str(job.id),
            "status" : job.status,
            "vm" : {},
            "progress" : job.progress
        }

        # Lxd monitoring data
        try:
            # TODO : to be reimplemented with pylxd api when this feature will be available :)
            out = subprocess.check_output(["lxc", "info", job.lxd_container])
            for l in out.decode().split('\n'):
                data = l.split(': ')
                if data[0].strip() in ["Name","Created", "Status", "Processes", "Memory (current)", "Memory (peak)"]:
                    result["vm"].update({data[0].strip(): data[1]})
            result.update({"vm_info" : True})
        except Exception as error:
            out = "No virtual machine available for this job."
            result.update({"vm" : out, "vm_info" : False})

        # Logs tails
        try: 
            out_tail = subprocess.check_output(["tail", os.path.join(RUNS_DIR, job.lxd_container, "logs/out.log"), "-n", "100"]).decode()
        except Exception as error:
            out_tail = "No stdout log of the job."

        try: 
            err_tail = subprocess.check_output(["tail", os.path.join(RUNS_DIR, job.lxd_container, "logs/err.log"), "-n", "100"]).decode()
        except Exception as error:
            err_tail = "No stderr log of the job."

        result.update({
            "out_tail" : out_tail, 
            "err_tail" : err_tail
        })
        return result





# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# INIT OBJECTS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 




pirus = Core()