#!env/python3
# coding: utf-8
import os
import uuid
import json
import yaml
import tarfile

from config import *
from core.framework import *
from core.model import *




class LxdManager(PirusManager):
    """
        Pirus manager to run pipeline from LXD container
    """
    def __init__(self):
        self.supported_features = {
            "pause_job" : True,
            "stop_job" : True,
            "monitoring_job" : True
        }


    def install_pipeline(pipeline):
        """
            Perform the installation of a pipeline that use LXD container
        """
        if !pipeline or !isinstance(pipeline, Pipeline) or !isinstance(pipeline.image_file, File):
            raise RegovarException("Pipeline data error.")

        lxd_alias = str(uuid.uuid4())
        root_path = os.path.join(PIPELINES_DIR, lxd_alias)
        old_file_path = pipeline.image_file.path
        pipeline.image_file.path = os.path.join(root_path, pipeline.name)

        # 1- Copy file into final folder
        plog.info('I: Installation of the pipeline package : ' + root_path)
        os.makedirs(root_path)
        os.rename(old_file_path, pipeline.image_file.path)
        os.chmod(pipeline.image_file.path, 0o777)

        # 2- Extract pipeline metadata
        # TODO : instead of testing import json then yaml, loading only yaml should be enough. to be tested
        try:
            tar = tarfile.open(pipeline.image_file.path)
            tar_data = [info for info in tar.getmembers() if info.name == "metadata.yaml"]
            metadata = tar.extractfile(member=tar_data[0])
            metadata = metadata.read()
            try:
                # try json ?
                metadata = json.loads(metadata.decode())
            except:
                # try yaml ?
                metadata = yaml.load(metadata)
            metadata = metadata["pirus"]
        except:
            # TODO : manage error + remove package file
            plog.info('E:    [FAILLED] Extraction of ' + pipeline.image_file.path)
            raise RegovarException("XXXX", "Unable to extract package. Corrupted file or wrong format")
        plog.info('I:    [OK     ] Extraction of metadata from ' + pipeline.image_file.path)

        # 2- Check that mandatory fields exists
        missing = ""
        for k in MANIFEST["mandatory"].keys():
            if k not in metadata.keys():
                missing += k + ", "                
        if missing != "":
            missing = missing[:-2]
            plog.info('E:    [FAILLED] Checking validity of metadata (missing : ' + missing + ")")
            raise RegovarException("XXXX", "Bad pirus pipeline format. Mandory fields missing in the metadata : " + missing)
        plog.info('I:    [OK     ] Checking validity of metadata')

        # 3- Default value for optional fields in mandatory file
        for k in MANIFEST["default"].keys():
            if k not in metadata.keys():
                metadata[k] = MANIFEST["default"][k]

        # 4- Extract pirus technicals files from the tar file
        try:
            if metadata["form"] is not None:
                source     = os.path.join("rootfs",metadata['form'][1:] if metadata['form'][0]=="/" else metadata['form'])
                tar_data   = [info for info in tar.getmembers() if info.name == source]
                file       = tar.extractfile(member=tar_data[0])
                source     = os.path.join(root_path, source)
                form_file  = os.path.join(root_path, "form.json")
                with open(form_file, 'bw+') as f:
                    f.write(file.read())
            else :
                form_file = os.path.join(root_path, "form.json")
                with open(form_file, 'w+') as f:
                    f.write("{}")

            source = PIPELINE_DEFAULT_ICON_PATH
            icon_file = os.path.join(root_path, "icon.png")
            if metadata["icon"] is not None:
                source = os.path.join("rootfs",metadata['icon'][1:] if metadata['icon'][0]=="/" else metadata['icon'])
                tar_data = [info for info in tar.getmembers() if info.name == source]
                file = tar.extractfile(member=tar_data[0])
                source = os.path.join(root_path, source)
                icon_file = os.path.join(root_path, os.path.basename(metadata['icon']))
                with open(icon_file, 'bw+') as f:
                    f.write(file.read())
            else:
                shutil.copyfile(source, icon_file)
        except:
            # TODO : manage error + remove package file
            plog.info('E:    [FAILLED] Extraction of ' + pipeline.image_file.path)
            raise RegovarException("XXXX", "Error occure during extraction of pipeline technical files (form.json / icon)")
        plog.info('I:    [OK     ] Extraction of pipeline technical files (form.json / icon)')


        # 5- Save pipeline into database
        lxd_alias = LXD_IMAGE_PREFIX + lxd_alias
        metadata.update({
            "root_path"        : root_path,
            "lxd_inputs_path"  : metadata["inputs"],
            "lxd_outputs_path" : metadata["outputs"],
            "lxd_logs_path"    : metadata["logs"],
            "lxd_db_path"      : metadata["databases"],
            "lxd_run_cmd"      : metadata["run"],
            "form_file"        : form_file,
            "icon_file"        : icon_file,
            "lxd_alias"        : lxd_alias,
            "pipeline_file"    : pipeline.image_file.path,
            "size"             : pipeline.size,
            "upload_offset"    : pipeline.upload_offset,
            "status"           : "INSTALLING"
        })
        try:
            pipeline.import_data(metadata)
            pipeline.save()
        except Exception as err:
            # TODO : manage error
            print(err)
            plog.info('E:    [FAILLED] Save pipeline information in database.')
            raise RegovarException("XXXX", "Failed to save pipeling info into the database.")
        plog.info('I:    [OK     ] Save pipeline information in database with id='+ str(pipeline.id))

        # 6- Install lxd container
        cmd = ["lxc", "image", "import", pipeline.image_file.path, "--alias", lxd_alias]
        try:
            out_tmp = '/tmp/' + lxd_alias + '-out'
            err_tmp = '/tmp/' + lxd_alias + '-err'
            subprocess.call(cmd, stdout=open(out_tmp, "w"), stderr=open(err_tmp, "w"))

        except Exception as err:
            # TODO : manage error
            print(err)
            plog.info('E:    [FAILLED] Installation of the lxd image. ($: ' + " ".join(cmd) + ")")
            raise RegovarException("XXXX", "Failed to install pipeline lxd image.")


        err = open(err_tmp, "r").read()
        if err != "":
            # TODO : manage error
            plog.info('E:    [FAILLED] Lxd image. ($: ' + " ".join(cmd) + ")")
            plog.info('--------------------------')
            plog.info(err)
            plog.info('--------------------------')
            pipeline.delete()
            shutil.rmtree(root_path)
            raise RegovarException("XXXX", "Failed to install pipeline lxd image (" + err + ")")
        else:
            plog.info('I:    [OK     ] Installation of the lxd image.')

        # 7- Clean directory
        try:
            keep = [pipeline.image_file.path, form_file, icon_file]
            for f in os.listdir(root_path):
                fullpath = os.path.join(root_path, f)
                if fullpath not in keep:
                    if os.path.isfile(fullpath):
                        os.remove(fullpath)
                    else:
                        shutil.rmtree(fullpath)
        except Exception as err:
            # TODO : manage error, notify only admins
            print(err)
            plog.info('E:    [FAILLED] Cleaning repository.')
        plog.info('I:    [OK     ] Cleaning repository.')
        plog.info('I:    All fine. Pipeline is ready !')

        pipeline.status = "READY"
        pipeline.save()
        return pipeline



    def uninstall_pipeline(pipeline_id):
        """
            IMPLEMENTATION REQUIRED
            Uninstall the pipeline image according to the dedicated technology (LXD, Docker, Biobox, ...)
        """
        raise RegovarException("The abstract method \"uninstall_pipeline\" of PirusManager must be implemented.")



    def init_job(job_id):
        """
            IMPLEMENTATION REQUIRED
            Init a job by checking its settings (stored in database) and preparing the container for this job.
        """
        raise RegovarException("The abstract method \"init_job\" of PirusManager must be implemented.")


    def start_job(self, job):
        """
            (Re)Start the job execution. by unfreezing the 
        """
        if !isinstance(job, Job): raise RegovarException("Wrong job provided")

        if job.status in ["waiting", "pause"]:
            return self.start_next_time(job)
        elif job.status == "initializing":
            return self.start_first_time(job)


    def pause_job(self, job):
        """
            IMPLEMENTATION OPTIONAL (according to self.supported_features)
            Pause the execution of the job to save server resources by example
        """
        if !isinstance(job, Job): raise RegovarException("Wrong job provided")

        if job.status in ["waiting", "running"]:
            settings = json.loads(job.settings)
            subprocess.Popen(["lxc", "pause", settings["lxd_container"]])
            return True
        return False


    def stop_job(jself, ob_id):
        """
            IMPLEMENTATION OPTIONAL (according to self.supported_features)
            Stop the job. The job is canceled and the container shall be destroyed
        """
        raise RegovarException("The abstract method \"stop_job\" of PirusManager must be implemented.")


    def monitoring_job(self, job_id):
        """
            IMPLEMENTATION OPTIONAL (according to self.supported_features)
            Provide monitoring information about the execution of the job (log stdout/stderr) and container
            settings (CPU/RAM used, etc)
        """
        raise RegovarException("The abstract method \"monitoring_job\" of PirusManager must be implemented.")


    def terminate_job(self, job_id):
        """
            IMPLEMENTATION REQUIRED
            Clean temp resources created by the container (log shall be kept), copy outputs file from the container
            to the right place on the server, register them into the database and associates them to the job.
        """
        raise RegovarException("The abstract method \"terminate_job\" of PirusManager must be implemented.")












    def start_first_time():



    def start_next_time(self, job):
        try:
            settings = json.loads(job.settings)
            subprocess.Popen(["lxc", "start", settings["lxd_container"]])
            return True
        except Exception err:
            # TODO manage error
            return False