#!env/python3
# coding: utf-8 
import os

# HOST
HOST           = "dev1.absolumentg.fr"
PORT           = "8080"
VERSION        = "v1"
HOSTNAME       = HOST + ":" + PORT + "/" + VERSION


# FILESYSTEM
FILES_DIR     = "/var/tmp/pirus_" + VERSION + "/files"
TEMP_DIR      = "/var/tmp/pirus_" + VERSION + "/downloads"
DATABASES_DIR = "/var/tmp/pirus_" + VERSION + "/databases"
PIPELINES_DIR = "/var/tmp/pirus_" + VERSION + "/pipelines"
RUNS_DIR      = "/var/tmp/pirus_" + VERSION + "/runs"


# AUTOCOMPUTED VALUES
PIRUS_DIR      = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR   = os.path.join(PIRUS_DIR, "templates/")
ERROR_ROOT_URL = "api.pirus.org/errorcode/"
NOTIFY_URL     = "http://" + HOSTNAME + "/run/notify/"


# LXD
LXD_UID        = 165537
LXD_GID        = LXD_UID
LXD_MAX        = 2
LXD_PREFIX     = "pirus"
LXD_HDW_CONF = {
	"CPU"  : None,
	"CORE" : None,
	"RAM"  : None,
	"DISK" : None
}


# MANIFEST MANDATORY
MANIFEST_MANDATORY = {
	"name"        : "The displayed name of the pirus pipeline", 
	"version_api" : "The version of the pirus api used by the pipeline", 
	"inputs"      : "The absolute path in the pipeline lxd container to the directory where input files have to be mount.", 
	"outputs"     : "The absolute path in the pipeline lxd container to the directory where output files will be write.", 
	"inputs_allowed" : "The list of extension of supported input files. Extension shall be lowercase, with or without the first dot. Take care to order them to avoid confusion. By example 'tar.gz' must be placed before 'gz' as gz is also the end of the 'tar.gz' exetension, so Pirus need to check first if the file is a tar.gz before testing if it's a '.gz' file.",
	"logs"        : "The absolute path in the pipeline lxd container to the directory where logs files will be write. Note that out.log, err.log and pirus.log will be automatically created in this directory.",
	"run"         : "The absolute path in the pipeline lxd container to the executable file to run the pipeline.", 
	"databases"   : "The absolute path in the pipeline lxd container to the directory where common databases have to be mount.",
	"config.json" : "The absolute path in the pipeline lxd container to the json file use as default config for the run.",
	"form.json"   : "The absolute path in the pipeline lxd container to the json file use to describe the form that will be used by the user to configure the run."
}

