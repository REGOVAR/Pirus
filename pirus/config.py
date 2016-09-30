#!env/python3
# coding: utf-8 
import os

HOSTNAME = "dev1.absolumentg.fr:8080" # "localhost:8080"

ERROR_ROOT_URL = "api.pirus.org/errorcode/"
PIRUS_API_V  = "1.0.0"
PIPELINES_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipelines/")
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates/")
RUN_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs/") 

NOTIFY_URL   = 'http://' + HOSTNAME + '/run/notify/'
