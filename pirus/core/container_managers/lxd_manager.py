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




class LxdManager(PirusContainerManager):
    """
        Pirus manager to run pipeline from LXD container
    """
    def __init__(self):
        self.supported_features = {
            "pause_job" : True,
            "stop_job" : True,
            "monitoring_job" : True
        }




    def install_pipeline(self, pipeline):
        """
            Perform the installation of a pipeline that use LXD container
        """
        if not pipeline or not isinstance(pipeline, Pipeline) or not isinstance(pipeline.image_file, File):
            raise RegovarException("Pipeline data error.")

        lxd_alias = str(uuid.uuid4())
        root_path = os.path.join(PIPELINES_DIR, lxd_alias)
        old_file_path = pipeline.image_file.path
        pipeline.image_file.path = os.path.join(root_path, pipeline.name)

        # 1- Copy file into final folder
        plog.info('Installation of the pipeline package : ' + root_path)
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
            plog.err('FAILLED Extraction of ' + pipeline.image_file.path)
            raise RegovarException("XXXX", "Unable to extract package. Corrupted file or wrong format")
        plog.info('Extraction of metadata from ' + pipeline.image_file.path)

        # 2- Check that mandatory fields exists
        missing = ""
        for k in MANIFEST["mandatory"].keys():
            if k not in metadata.keys():
                missing += k + ", "                
        if missing != "":
            missing = missing[:-2]
            plog.err('FAILLED Checking validity of metadata (missing : ' + missing + ")")
            raise RegovarException("XXXX", "Bad pirus pipeline format. Mandory fields missing in the metadata : " + missing)
        plog.info('Checking validity of metadata')

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
            plog.err('FAILLED Extraction of ' + pipeline.image_file.path)
            raise RegovarException("XXXX", "Error occure during extraction of pipeline technical files (form.json / icon)")
        plog.info('Extraction of pipeline technical files (form.json / icon)')


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
            plog.err('FAILLED Save pipeline information in database.')
            raise RegovarException("XXXX", "Failed to save pipeling info into the database.")
        plog.info('Save pipeline information in database with id='+ str(pipeline.id))

        # 6- Install lxd container
        cmd = ["lxc", "image", "import", pipeline.image_file.path, "--alias", lxd_alias]
        try:
            out_tmp = '/tmp/' + lxd_alias + '-out'
            err_tmp = '/tmp/' + lxd_alias + '-err'
            subprocess.call(cmd, stdout=open(out_tmp, "w"), stderr=open(err_tmp, "w"))

        except Exception as err:
            # TODO : manage error
            print(err)
            plog.err('FAILLED Installation of the lxd image. ($: ' + " ".join(cmd) + ")")
            raise RegovarException("XXXX", "Failed to install pipeline lxd image.")


        err = open(err_tmp, "r").read()
        if err != "":
            # TODO : manage error
            plog.err('FAILLED Lxd image. ($: ' + " ".join(cmd) + ")")
            plog.info('--------------------------')
            plog.info(err)
            plog.info('--------------------------')
            pipeline.delete()
            shutil.rmtree(root_path)
            raise RegovarException("XXXX", "Failed to install pipeline lxd image (" + err + ")")
        else:
            plog.info('Installation of the lxd image.')

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
            plog.err('FAILLED Cleaning repository.')
        plog.info('Cleaning repository.')
        plog.info('All fine. Pipeline is ready !')

        pipeline.status = "READY"
        pipeline.save()
        return pipeline



    async def uninstall_pipeline(pipeline_id):
        """
            IMPLEMENTATION REQUIRED
            Uninstall the pipeline image according to the dedicated technology (LXD, Docker, Biobox, ...)
        """
        raise RegovarException("The abstract method \"uninstall_pipeline\" of PirusManager must be implemented.")



    def init_job(job_id):
        j = Job.from_id
        return j


    def start_job(self, job):
        """
            (Re)Start the job execution. by unfreezing the 
        """
        if not isinstance(job, Job): raise RegovarException("Wrong job provided")

        if job.status in ["waiting", "pause"]:
            return self.start_next_time(job)
        elif job.status == "initializing":
            return self.start_first_time(job)


    def pause_job(self, job):
        """
            IMPLEMENTATION OPTIONAL (according to self.supported_features)
            Pause the execution of the job to save server resources by example
        """
        if not isinstance(job, Job): raise RegovarException("Wrong job provided")

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












    def start_next_time(self, job):
        try:
            settings = json.loads(job.settings)
            subprocess.Popen(["lxc", "start", settings["lxd_container"]])
            return True
        except Exception as err:
            # TODO manage error
            return False



    def start_first_time():
        print("INITIALIZING !")
        self.notify_status("INITIALIZING")

        #LXD ready ! Prepare filesystem of the server to host lxc container files
        root_path    = os.path.join(RUNS_DIR, run.lxd_container)
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
        data = json.loads(run.config)
        with open(conf_file, 'w') as f:
            f.write(json.dumps(data, sort_keys=True, indent=4))
            os.chmod(conf_file, 0o777)

        for file_id in run.inputs:
            f = PirusFile.from_id(file_id)
            link_path = os.path.join(inputs_path, f.name)
            os.link(f.path, link_path)
            os.chmod(link_path, 0o644)

        # Setting up the lxc container for the run
        try:
            pipeline = Pipeline.from_id(run.pipeline_id)
            # create run file
            run_file = os.path.join(root_path, "start_" + run.lxd_container + ".sh")
            print(run_file)
            with open(run_file, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write(pipeline.lxd_run_cmd + " 1> " + os.path.join(pipeline.lxd_logs_path, 'out.log') + " 2> " + os.path.join(pipeline.lxd_logs_path, "err.log\n")) #  || curl -X POST -d '{\"status\" : \"ERROR\"}' " + run.notify_url + "
                f.write("chown -Rf " + str(PIRUS_UID) + ":" + str(PIRUS_GID) + " " + pipeline.lxd_outputs_path + "\n")
                f.write("curl -X POST -d '{\"status\" : \"FINISHING\"}' " + run.notify_url + "\n")
                os.chmod(run_file, 0o777)

            # create container
            subprocess.call(["lxc", "init", run.lxd_image, run.lxd_container])
            # set up env
            subprocess.call(["lxc", "config", "set", run.lxd_container, "environment.PIRUS_NOTIFY_URL", self.notify_url ])
            subprocess.call(["lxc", "config", "set", run.lxd_container, "environment.PIRUS_CONFIG_FILE", os.path.join(pipeline.lxd_inputs_path, "config.json") ])
            # set up devices
            subprocess.call(["lxc", "config", "device", "add", run.lxd_container, "pirus_inputs",  "disk", "source="+inputs_path,   "path=" + pipeline.lxd_inputs_path[1:], "readonly=True"])
            subprocess.call(["lxc", "config", "device", "add", run.lxd_container, "pirus_outputs", "disk", "source="+outputs_path,  "path=" + pipeline.lxd_outputs_path[1:]])
            subprocess.call(["lxc", "config", "device", "add", run.lxd_container, "pirus_logs",    "disk", "source="+logs_path,     "path=" + pipeline.lxd_logs_path[1:]])
            subprocess.call(["lxc", "config", "device", "add", run.lxd_container, "pirus_db",      "disk", "source="+DATABASES_DIR, "path=" + pipeline.lxd_db_path[1:], "readonly=True"])
        except:
            return self.error('Unexpected error ' + str(sys.exc_info()[0]))
            raise 

        # Run the pipe !
        try:
            subprocess.call(["lxc", "start", run.lxd_container])
            lxd_run_file = os.path.join("/", os.path.basename(run_file))
            subprocess.call(["lxc", "file", "push", run_file, run.lxd_container + lxd_run_file])
            # for file_id in run.inputs:
            #     f = PirusFile.from_id(file_id)
            #     print ("push " + f.path + " to " + run.lxd_container + os.path.join(pipeline.lxd_inputs_path, f.name))
            #     subprocess.call(["lxc", "file", "push", f.path, run.lxd_container + os.path.join(pipeline.lxd_inputs_path, f.name)])
            subprocess.call(["lxc", "exec", run.lxd_container, "--",  "chmod", "+x", lxd_run_file])
            subprocess.Popen(["lxc", "exec", run.lxd_container, lxd_run_file])
            self.notify_status("RUNNING")
        except:
            return self.error('Unexpected error ' + str(sys.exc_info()[0])) 
            raise