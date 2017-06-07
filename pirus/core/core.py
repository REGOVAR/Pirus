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
from core.framework.common import *
from core.model import *
from core.managers import *






# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# CORE OBJECT
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

def notify_all_print(msg=None, src=None):
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
        

        # method handler to notify all
        # according to api that will be pluged on the core, this method should be overriden 
        # to really do a notification. (See how api_rest override this method)
        self.notify_all = notify_all_print




# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# INIT OBJECTS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 



# Pirus core
core = Core()