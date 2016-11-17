#!env/python3
# coding: utf-8 
import os

# HOST
HOST           = "dev1.absolumentg.fr"
PORT           = "8081"
VERSION        = "tu"
HOSTNAME       = HOST + ":" + PORT + "/" + VERSION


RANGE_DEFAULT = 20
RANGE_MAX     = 1000

# DB
DATABASE_NAME = "pirus_tu"


# FILESYSTEM
FILES_DIR     = "/tmp/pirus_unittest/files"
TEMP_DIR      = "/tmp/pirus_unittest/downloads"
DATABASES_DIR = "/tmp/pirus_unittest/databases"
PIPELINES_DIR = "/tmp/pirus_unittest/pipelines"
RUNS_DIR      = "/tmp/pirus_unittest/runs"


# AUTOCOMPUTED VALUES
PIRUS_DIR      = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR   = os.path.join(PIRUS_DIR, "api_rest/templates/")
ERROR_ROOT_URL = "api.pirus.org/errorcode/"
NOTIFY_URL     = "http://" + HOSTNAME + "/run/notify/"


# LXD
PIRUS_UID      = 1000
PIRUS_GID      = PIRUS_UID
LXD_UID        = 165537
LXD_GID        = LXD_UID
LXD_MAX        = 2
LXD_CONTAINER_PREFIX  = "pirus-run-"
LXD_IMAGE_PREFIX      = "pirus-pipe-"
LXD_HDW_CONF = {
    "CPU"  : None,
    "CORE" : None,
    "RAM"  : None,
    "DISK" : None
}


# MANIFEST fields in the pirus pipeline package
MANIFEST = {
    "mandatory" : {
        "name"        : "The displayed name of the pirus pipeline", 
        "run"         : "The command line that will executed by pirus to run the pipeline.", 
    },
    "default" : {
        "pirus_api"   : VERSION,               # The version of the pirus api used by the pipeline
        "inputs"      : "/pipeline/inputs",    # The absolute path in the pipeline lxd container to the directory where input files have to be mount.
        "outputs"     : "/pipeline/outputs",   # The absolute path in the pipeline lxd container to the directory where output files will be write.
        "logs"        : "/pipeline/logs",      # The absolute path in the pipeline lxd container to the directory where logs files will be write. Note that out.log, err.log and pirus.log will be automatically created in this directory.
        "databases"   : "/pipeline/databases", # The absolute path in the pipeline lxd container to the directory where common databases have to be mount.
        "form"        : None,                  # The absolute path in the pipeline lxd container to the json file use to describe the form that will be used by the user to configure the run.
        "icon"          : None,                  # The absolute path in the pipeline lxd container to the icon of the pipe.
    }
}


PIPELINE_DEFAULT_ICON_PATH = os.path.join(TEMPLATE_DIR , "pipeline_icon.png")
