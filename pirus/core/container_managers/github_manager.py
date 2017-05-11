#!env/python3
# coding: utf-8
import os
import uuid
import json
import yaml
import tarfile
import ipdb
import subprocess

from config import *
from core.framework import *
from core.model import *




class GithubManager(PirusContainerManager):
    """
        Pirus manager to run pipeline stored on github into a LXD container
    """
    def __init__(self):
        # To allow the core to know if this kind of pipeline need an image to be donwloaded for the installation
        self.need_image_file = False
        # Job's control features supported by this bind of pipeline
        self.supported_features = {
            "pause_job" : True,
            "stop_job" : True,
            "monitoring_job" : True
        }

        if not CONTAINERS_CONFIG or "lxd" not in CONTAINERS_CONFIG.keys() or not CONTAINERS_CONFIG["lxd"]:
            raise RegovarException("No configuration settings found for lxd")
        self.config = CONTAINERS_CONFIG["lxd"]



    def install_pipeline(self, pipeline):
        """
            Perform the installation of a pipeline that use LXD container
        """
        if not pipeline or not isinstance(pipeline, Pipeline) :
            raise RegovarException("Pipeline's data error.")
        pipeline.load_depth(1)
        if not pipeline.image_file or not pipeline.image_file.path:
            raise RegovarException("Pipeline image file's data error.")

        # 0- retrieve conf related to LXD
        if not CONTAINERS_CONFIG or "lxd" not in CONTAINERS_CONFIG.keys() or not CONTAINERS_CONFIG["lxd"]:
            raise RegovarException("No configuration settings found for lxd")
        conf = CONTAINERS_CONFIG["lxd"]
        lxd_alias = str(uuid.uuid4())
        root_path = os.path.join(PIPELINES_DIR, lxd_alias)
        old_file_path = pipeline.image_file.path
        pipeline.image_file.path = os.path.join(root_path, pipeline.name)
        
        # 1- Copy file into final folder
        log('Installation of the pipeline package : ' + root_path)
        os.makedirs(root_path)
        os.rename(old_file_path, pipeline.image_file.path)
        os.chmod(pipeline.image_file.path, 0o777)

        # 2- Extract pipeline metadata
        try:
            tar = tarfile.open(pipeline.image_file.path)
            tar_data = [info for info in tar.getmembers() if info.name == "metadata.yaml"]
            metadata = tar.extractfile(member=tar_data[0])
            metadata = metadata.read()
            metadata = yaml.load(metadata)  # using yaml as it can also load json
            metadata = metadata["pirus"]
        except:
            # TODO : manage error + remove package file
            err('FAILLED Extraction of ' + pipeline.image_file.path)
            raise RegovarException("XXXX", "Unable to extract package. Corrupted file or wrong format")
        log('Extraction of metadata from ' + pipeline.image_file.path)

        # 2- Check that mandatory fields exists
        missing = ""
        for k in conf["manifest"]["mandatory"].keys():
            if k not in metadata.keys():
                missing += k + ", "                
        if missing != "":
            missing = missing[:-2]
            raise RegovarException("FAILLED Checking validity of metadata (missing : {})".format(missing))
        log('Validity of metadata checked')

        # 3- Default value for optional fields in mandatory file
        for k in conf["manifest"]["default"].keys():
            if k not in metadata.keys():
                metadata[k] = conf["manifest"]["default"][k]

        # 4- Extract pirus technicals files from the tar file
        try:
            if metadata["form"] is not None:
                source = os.path.join("rootfs",metadata['form'][1:] if metadata['form'][0]=="/" else metadata['form'])
                tar_data = [info for info in tar.getmembers() if info.name == source]
                file = tar.extractfile(member=tar_data[0])
                source = os.path.join(root_path, source)
                form_file = os.path.join(root_path, "form.json")
                ui_form = file.read()
                with open(form_file, 'bw+') as f:
                    f.write(ui_form)
            else :
                form_file = os.path.join(root_path, "form.json")
                form_file = b'{}'
                with open(form_file, 'bw+') as f:
                    f.write(form_file)

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
        except Exception as err:
            raise RegovarException("Error occure during extraction of pipeline technical files (form.json / icon) from image file : {}".format(pipeline.image_file.path), "", err)
        log('Extraction of pipeline technical files (form.json / icon)')

        # 5- Save pipeline into database
        lxd_alias = conf["image_name"].format(lxd_alias)
        metadata["lxd_alias"] = lxd_alias
        pipeline.load(metadata)
        pipeline.vm_settings = yaml.dump(metadata)
        pipeline.status = "installing"
        pipeline.ui_form = ui_form.decode()
        pipeline.ui_icon = icon_file
        pipeline.root_path = root_path
        pipeline.save()
        log("Pipeline saved in database with id={}".format(pipeline.id))

        # 6- Install lxd container
        cmd = ["lxc", "image", "import", pipeline.image_file.path, "--alias", lxd_alias]
        try:
            out_tmp = '/tmp/' + lxd_alias + '-out'
            err_tmp = '/tmp/' + lxd_alias + '-err'
            subprocess.call(cmd, stdout=open(out_tmp, "w"), stderr=open(err_tmp, "w"))
        except Exception as err:
            raise RegovarException("FAILLED Installation of the lxd image. ($: {})\nPlease, check logs {}".format(" ".join(cmd), err_tmp), "", err)
        err = open(err_tmp, "r").read()
        if err != "":
            pipeline.delete()
            shutil.rmtree(root_path)
            raise RegovarException("FAILLED Lxd image. ($: {})".format(" ".join(cmd)), "", err)
        else:
            log('Installation of the lxd image.')

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
            # Notify only admins
            err('FAILLED to clean repository : {}'.format(err))
        log('Cleaning repository.')
        log('Pipeline is ready !')

        pipeline.status = "ready"
        pipeline.save()
        return pipeline




    def uninstall_pipeline(self, pipeline):
        """
            Uninstall the pipeline lxd image.
            Database & filesystem clean is done by the core
        """
        if not pipeline or not isinstance(pipeline, Pipeline) :
            raise RegovarException("Pipeline's data error.")
        # Retrieve container settings
        settings = yaml.load(pipeline.vm_settings)
        lxd_alias = settings["lxd_alias"]
        # Install lxd container
        cmd = ["lxc", "image", "delete", lxd_alias]
        try:
            out_tmp = '/tmp/' + lxd_alias + '-out'
            err_tmp = '/tmp/' + lxd_alias + '-err'
            subprocess.call(cmd, stdout=open(out_tmp, "w"), stderr=open(err_tmp, "w"))
        except Exception as err:
            raise RegovarException("FAILLED Removing the lxd image {}. ($: {})\nPlease, check logs {}".format(lxd_alias, " ".join(cmd), err_tmp), "", err)








    def init_job(self, job):
        """
            Init a job :
            - check settings (stored in database) 
            - create the lxd container from pipeline image
            - configure container and mount I/O directories to the filesystem
        """
        # Setting up the lxc container for the job
        lxd_container = self.config["job_name"].format("{}-{}".format(job.pipeline_id, job.id))
        root_path = os.path.join(JOBS_DIR, lxd_container)
        vm_settings = yaml.load(job.pipeline.vm_settings)
        lxd_job_cmd = vm_settings["run"]
        lxd_logs_path = vm_settings["logs"]
        lxd_inputs_path = vm_settings["inputs"]
        lxd_outputs_path = vm_settings["outputs"]
        lxd_db_path = vm_settings["databases"]
        lxd_image = vm_settings["lxd_alias"]
        notify_url = NOTIFY_URL.format(job.id)

        try:
            # create job's start command file
            job_file = os.path.join(root_path, "start_" + lxd_container + ".sh")
            print(job_file)
            with open(job_file, 'w') as f:
                f.write("#!/bin/bash\n")
                # TODO : catch if execution return error and notify pirus with error status
                f.write("{} 1> {} 2> {}".format(lxd_job_cmd, os.path.join(lxd_logs_path, 'out.log'), os.path.join(lxd_logs_path, "err.log\n"))) #  || curl -X POST -d '{\"status\" : \"error\"}' " + notify_url + "
                f.write("chown -Rf {}:{} {}\n".format(self.config["pirus_uid"], self.config["pirus_gid"], lxd_outputs_path))
                f.write("curl -X POST -d '{\"status\" : \"finalizing\"}' {}\n".format(notify_url))
                os.chmod(job_file, 0o777)
            # create container
            subprocess.call(["lxc", "init", lxd_image, lxd_container])
            # set up env
            subprocess.call(["lxc", "config", "set", lxd_container, "environment.PIRUS_NOTIFY_URL", notify_url ])
            subprocess.call(["lxc", "config", "set", lxd_container, "environment.PIRUS_CONFIG_FILE", os.path.join(lxd_inputs_path, "config.json") ])
            # set up devices
            subprocess.call(["lxc", "config", "device", "add", lxd_container, "pirus_inputs",  "disk", "source=" + inputs_path,   "path=" + lxd_inputs_path[1:], "readonly=True"])
            subprocess.call(["lxc", "config", "device", "add", lxd_container, "pirus_outputs", "disk", "source=" + outputs_path,  "path=" + lxd_outputs_path[1:]])
            subprocess.call(["lxc", "config", "device", "add", lxd_container, "pirus_logs",    "disk", "source=" + logs_path,     "path=" + lxd_logs_path[1:]])
            subprocess.call(["lxc", "config", "device", "add", lxd_container, "pirus_db",      "disk", "source=" + DATABASES_DIR, "path=" + lxd_db_path[1:], "readonly=True"])
        except Exception as err:
            raise RegovarException("Unexpected error.", "", err)

        # Execute the "run" command to start the pipe
        try:
            subprocess.call(["lxc", "start", lxd_container])
            lxd_job_file = os.path.join("/", os.path.basename(job_file))
            subprocess.call(["lxc", "file", "push", job_file, lxd_container + lxd_job_file])
            subprocess.call(["lxc", "exec", lxd_container, "--",  "chmod", "+x", lxd_job_file])
            subprocess.Popen(["lxc", "exec", lxd_container, lxd_job_file])
        except Exception as err:
            raise RegovarException("Unexpected error.", "", err)

        return True

        





    def start_job(self, job):
        """
            (Re)Start the job execution. By unfreezing the 
        """
        # Setting up the lxc container for the job
        lxd_container = self.config["job_name"].format("{}-{}".format(job.pipeline_id, job.id))
        return subprocess.Popen(["lxc", "start", lxd_container]) == 0






    def pause_job(self, job):
        """
            Pause the execution of the job.
        """
        lxd_container = self.config["job_name"].format("{}-{}".format(job.pipeline_id, job.id))
        return subprocess.Popen(["lxc", "pause", lxd_container]) == 0




    def stop_job(self, job):
        """
            Stop the job. The job is canceled and the container is destroyed.
        """
        lxd_container = self.config["job_name"].format("{}-{}".format(job.pipeline_id, job.id))
        return subprocess.Popen(["lxc", "delete", run.lxd_container, "--force"]) == 0



    def monitoring_job(self, job_id):
        """
            Provide monitoring information about the execution of the job (log stdout/stderr) and container
            settings (CPU/RAM used, etc)
        """
        lxd_container = self.config["job_name"].format("{}-{}".format(job.pipeline_id, job.id))
        # Result
        result = {
            "name" : run.name,
            "pipeline_icon" : pipeline.icon_url,
            "pipeline_name" : pipeline.name,
            "id" : str(run.id),
            "status" : run.status,
            "vm" : {},
            "progress" : run.progress
        }
        # Lxd monitoring data
        try:
            # TODO : to be reimplemented with pylxd api when this feature will be available :)
            out = subprocess.check_output(["lxc", "info", run.lxd_container])
            for l in out.decode().split('\n'):
                data = l.split(': ')
                if data[0].strip() in ["Name","Created", "Status", "Processes", "Memory (current)", "Memory (peak)"]:
                    result["vm"].update({data[0].strip(): data[1]})
            result.update({"vm_info" : True})
        except Exception as error:
            out = "No virtual machine available for this run."
            result.update({"vm" : out, "vm_info" : False})

        # Logs tails
        try: 
            out_tail = subprocess.check_output(["tail", os.path.join(RUNS_DIR, run.lxd_container, "logs/out.log"), "-n", "100"]).decode()
        except Exception as error:
            out_tail = "No stdout log of the run."

        try: 
            err_tail = subprocess.check_output(["tail", os.path.join(RUNS_DIR, run.lxd_container, "logs/err.log"), "-n", "100"]).decode()
        except Exception as error:
            err_tail = "No stderr log of the run."

        result.update({
            "out_tail" : out_tail, 
            "err_tail" : err_tail
        })
        return result



    def terminate_job(self, job_id):
        """
            IMPLEMENTATION REQUIRED
            Clean temp resources created by the container (log shall be kept), copy outputs file from the container
            to the right place on the server, register them into the database and associates them to the job.
        """
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





