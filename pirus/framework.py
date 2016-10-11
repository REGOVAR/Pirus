#!env/python3
# coding: utf-8

import datetime
import aiohttp
import aiohttp_jinja2
import jinja2
import logging
import uuid
import hashlib


from aiohttp import web
from config import *


# Common tools


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



def rest_success(response_data=None, pagination_data=None):
    """ 
        Build the REST success response that will encapsulate the given data (in python dictionary format)
        :param response_data:   The data to wrap in the JSON success response
        :param pagination_data: The data regarding the pagination
    """
    if response_data is None:
        results = {"success":True}
    else:
        results = {"success":True, "data":response_data}
    if pagination_data is not None:
        results.update(pagination_data)
    return web.json_response(results)



def rest_error(message:str="Unknow", code:str="0", error_id:str=""):
    """ 
        Build the REST error response
        :param message:         The short "friendly user" error message
        :param code:            The code of the error type
        :param error_id:        The id of the error, to return to the end-user. 
                                This code will allow admins to find in logs where exactly this error occure
    """
    results = {
        "success":              False, 
        "msg":                  message, 
        "error_code":   code, 
        "error_url":    ERROR_ROOT_URL + code,
        "error_id":             error_id
    }
    return web.json_response(results)



def get_pipeline_forlder_name(name:str):
    cheked_name = ""
    for l in name:
        if l.isalnum() or l in [".", "-", "_"]:
            cheked_name += l
        if l == " ":
            cheked_name += "_"
    return cheked_name;




def plugin_running_task(task_id):
    result = execute_plugin.AsyncResult(task_id)
    return result.get()









def humansize(nbytes):
    suffixes = ['b', 'Ko', 'Mo', 'Go', 'To', 'Po']
    if nbytes == 0: return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()





class PirusException(Exception):
    msg  = "Unknow error :/"
    code = "0000"
    id   = None
    date = None

    def __str__(self):
        return "[ERROR:" + code + "] " + str(self.id) + " : " + self.msg

    def __init__(self, code:str, msg:str, logger=None):
        self.code = code
        self.msg = msg
        self.id = str(uuid.uuid4())
        self.date = datetime.datetime.utcnow().timestamp()

        if logger != None:
            logger.err(msg)



# Create server app
setup_logger('pirus', os.path.join(PIRUS_DIR, "pirus.log"))
plog = logging.getLogger('pirus')
plog.info('I: Pirus server initialisation')
plog.info('I: Config loaded :')
plog.info('I:    HOST           : ' + HOST)
plog.info('I:    PORT           : ' + PORT)
plog.info('I:    VERSION        : ' + VERSION)
plog.info('I:    HOSTNAME       : ' + HOSTNAME)
plog.info('I:    FILES_DIR      : ' + FILES_DIR)
plog.info('I:    TEMP_DIR       : ' + TEMP_DIR)
plog.info('I:    DATABASES_DIR  : ' + DATABASES_DIR)
plog.info('I:    PIPELINES_DIR  : ' + PIPELINES_DIR)
plog.info('I:    RUNS_DIR       : ' + RUNS_DIR)
plog.info('I:    PIRUS_DIR      : ' + PIRUS_DIR)
plog.info('I:    TEMPLATE_DIR   : ' + TEMPLATE_DIR)
plog.info('I:    ERROR_ROOT_URL : ' + ERROR_ROOT_URL)
plog.info('I:    NOTIFY_URL     : ' + NOTIFY_URL)
plog.info('I:    LXD_UID        : ' + str(LXD_UID))
plog.info('I:    LXD_GID        : ' + str(LXD_GID))
plog.info('I:    LXD_MAX        : ' + str(LXD_MAX))
plog.info('I:    LXD_PREFIX     : ' + LXD_PREFIX)


app = web.Application()
plog.info('I: iaoHTTP server started')
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(TEMPLATE_DIR))

