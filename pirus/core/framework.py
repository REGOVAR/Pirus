#!env/python3
# coding: utf-8
import os
import datetime
import logging
import uuid
import time
import asyncio
import subprocess
import config as C


from config import LOG_DIR



#
# As Pirus is a subproject of Regovar, thanks to keep framework complient
# TODO : find a way to manage it properly with github (subproject ?)
#

# =====================================================================================================================
# GENERIC TOOLS
# =====================================================================================================================
asyncio_main_loop = asyncio.get_event_loop()
def run_until_complete(future):
    """
        Allow calling of an async method into a "normal" method (which is not a coroutine)
    """
    asyncio_main_loop.run_until_complete(future)


def run_async(future, *args):
    """
        Call a "normal" method into another thread 
        (don't block the caller method, but cannot retrieve result)
    """
    asyncio_main_loop.run_in_executor(None, future, *args)



# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# TOOLS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

def exec_cmd(cmd):
    """
        execute a system command and return the stdout result
    """
    out_tmp = '/tmp/test_out'
    err_tmp = '/tmp/test_err'
    res = subprocess.call(cmd, stdout=open(out_tmp, "w"), stderr=open(err_tmp, "w"))
    out = open(out_tmp, "r").read()
    err = open(err_tmp, "r").read()
    return res, out, err
    

def get_pipeline_forlder_name(name:str):
    """
        Todo : doc
    """
    cheked_name = ""
    for l in name:
        if l.isalnum() or l in [".", "-", "_"]:
            cheked_name += l
        if l == " ":
            cheked_name += "_"
    return cheked_name;




def plugin_running_task(task_id):
    """
        Todo : doc
    """
    result = execute_plugin.AsyncResult(task_id)
    return result.get()








def humansize(nbytes):
    """
        Todo : doc
    """
    suffixes = ['o', 'Ko', 'Mo', 'Go', 'To', 'Po']
    if nbytes == 0: return '0 o'
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def md5(file_path):
    """
        Todo : doc
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()






# =====================================================================================================================
# LOGS MANAGEMENT
# =====================================================================================================================


def setup_logger(logger_name, log_file, level=logging.INFO):
    """
        Todo : doc
    """
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)s | %(message)s')
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    l.setLevel(level)
    l.addHandler(fileHandler)
    l.addHandler(streamHandler)


def log(msg):
    global rlog
    rlog.info(msg)


def war(msg):
    global rlog
    rlog.warning(msg)


def err(msg, exception=None):
    global rlog
    rlog.error(msg)
    if exception and not isinstance(exception, RegovarException):
        # To avoid to log multiple time the same exception when chaining try/catch
        rlog.exception(exception)





# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# ERROR MANAGEMENT
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 




class RegovarException(Exception):
    """
        Regovar exception
    """
    msg = "Unknow error :/"
    code = "E000000"

    def __init__(self, msg: str, code: str=None, exception: Exception=None, logger: logging.Logger=None):
        self.code = code or RegovarException.code
        self.msg = msg or RegovarException.msg
        self.id = str(uuid.uuid4())
        self.date = datetime.datetime.utcnow().timestamp()
        self.log = "ERROR {} [{}] {}".format(self.code, self.id, self.msg)

        if logger:
            logger.error(self.log)
            if exception and not isinstance(exception, RegovarException):
                # To avoid to log multiple time the same exception when chaining try/catch
                logger.exception(exception)
        else:
            err(self.log, exception)


    def __str__(self):
        return self.log


def log_snippet(longmsg, exception: RegovarException=None):
    """
        Log the provided msg into a new log file and return the generated log file
        To use when you want to log a long text (like a long generated sql query by example) to 
        avoid to poluate the main log with too much code.
    """
    uid = exception.id if exception else str(uuid.uuid4())
    filename = os.path.join(LOG_DIR,"snippet_{}.log".format(uid))
    with open(filename, 'w+') as f:
        f.write(longmsg)
    return filename






# =====================================================================================================================
# PIRUS CORE - Container Manager Abstracts
# =====================================================================================================================

class PirusContainerManager():
    """
        This abstract method shall be overrided by all pirus managers.
        Pirus managers clain to manage virtualisation of job with a specific technologie.
        Pirus managers implementations are in the core/managers/ directory
    """
    def __init__(self):
        # To allow the core to know if this kind of pipeline need an image to be donwloaded for the installation
        self.need_image_file = True
        # Job's control features supported by this bind of pipeline
        self.supported_features = {
            "pause_job" : False,
            "stop_job" : False,
            "monitoring_job" : False
        }


    def install_pipeline(self, pipeline):
        """
            IMPLEMENTATION REQUIRED
            Install the pipeline image according to the dedicated technology (LXD, Docker, Biobox, ...)
            Return True if success; False otherwise
        """
        raise NotImplementedError("The abstract method \"install_pipeline\" of PirusManager must be implemented.")


    def uninstall_pipeline(self, pipeline):
        """
            IMPLEMENTATION REQUIRED
            Uninstall the pipeline image according to the dedicated technology (LXD, Docker, Biobox, ...)
            Note that Database and filesystem clean is done by the core. 

            Return True if success; False otherwise
        """
        raise NotImplementedError("The abstract method \"uninstall_pipeline\" of PirusManager must be implemented.")



    def init_job(self, job):
        """
            IMPLEMENTATION REQUIRED
            Init a job by checking its settings (stored in database) and preparing the container for this job.
            Return void. Must raise exception in case of error
        """
        raise NotImplementedError("The abstract method \"init_job\" of PirusManager must be implemented.")


    def start_job(self, job):
        """
            IMPLEMENTATION REQUIRED
            Start the job into the container. The container may already exists as this method can be call
            after init_job and pause_job.
            Return True if success; False otherwise
        """
        raise NotImplementedError("The abstract method \"start_job\" of PirusManager must be implemented.")


    def pause_job(self, job):
        """
            IMPLEMENTATION OPTIONAL (according to self.supported_features)
            Pause the execution of the job to save server resources by example
            Return True if success; False otherwise
        """
        if self.supported_features["pause_job"]:
            raise RegovarException("The abstract method \"pause_job\" of PirusManager shall be implemented.")


    def stop_job(self, job):
        """
            IMPLEMENTATION OPTIONAL (according to self.supported_features)
            Stop the job. The job is canceled and the container shall be destroyed
            Return True if success; False otherwise
        """
        if self.supported_features["stop_job"]:
            raise RegovarException("The abstract method \"stop_job\" of PirusManager shall be implemented.")


    def monitoring_job(self, job):
        """
            IMPLEMENTATION OPTIONAL (according to self.supported_features)
            Provide monitoring information about the container (CPU/RAM used, etc)
            This method is always called synchronously, so take care to not take to much time to retrieve informations
            Return monitoring information as json.
        """
        if self.supported_features["monitoring_job"]:
            raise RegovarException("The abstract method \"monitoring_job\" of PirusManager shall be implemented.")


    def finalize_job(self, job):
        """
            IMPLEMENTATION REQUIRED
            Clean temp resources created by the container (log shall be kept)
            Return True if success; False otherwise
        """
        raise NotImplementedError("The abstract method \"terminate_job\" of PirusManager must be implemented.")

















# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# INIT OBJECTS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# Create pirus logger : plog
setup_logger('pirus', os.path.join(LOG_DIR, "pirus.log"))
rlog = logging.getLogger('pirus')
