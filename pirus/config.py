#!env/python3
# coding: utf-8 
import os

# HOST
HOST           = "dev1.absolumentg.fr"
PORT           = "8080"
VERSION        = "v1"
HOSTNAME       = HOST + ":" + PORT + "/" + VERSION


# FILESYSTEM
INPUTS_DIR    = "/var/tmp/pirus_" + VERSION + "/inputs"
INPUTS_TEMP   = "/var/tmp/pirus_" + VERSION + "/downloads"
OUTPUTS_DIR   = "/var/tmp/pirus_" + VERSION + "/outputs"
DATABASES_DIR = "/var/tmp/pirus_" + VERSION + "/databases"
PIPELINES_DIR = "/var/tmp/pirus_" + VERSION + "/pipelines"
RUNS_DIR      = "/var/tmp/pirus_" + VERSION + "/runs"


# AUTOCOMPUTED VALUES
PIRUS_DIR      = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR   = os.path.join(PIRUS_DIR, "templates/")
ERROR_ROOT_URL = "api.pirus.org/errorcode/"
NOTIFY_URL     = "http://" + HOSTNAME + "/run/notify/"


# LXD
LXD_MAX        = 2
LXD_PREFIX     = "pirus_"
