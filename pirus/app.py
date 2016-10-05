#!env/python3
# coding: utf-8

import os

from aiohttp import web, MultiDict
from mongoengine import *



# Pirus package
from config import *
from pirus_worker import run_pipeline
from framework import app
from api_v1 import *



# Init logs
# TODO



# Create / Connect database
connect('pirus')



# CHECK filesystem
if not os.path.exists(RUNS_DIR):
	os.makedirs(RUNS_DIR)
if not os.path.exists(PIPELINES_DIR):
	os.makedirs(PIPELINES_DIR)
if not os.path.exists(INPUTS_DIR):
	os.makedirs(INPUTS_DIR)
if not os.path.exists(TEMP_DIR):
	os.makedirs(INPUTS_TEMP)
if not os.path.exists(DATABASES_DIR):
	os.makedirs(DATABASES_DIR)

if not os.path.exists(TEMPLATE_DIR):
	print("ERROR : Templates directory doesn't exists.", TEMPLATE_DIR)




# CHECK consistensy between database and filesystem





# Start the pirus server
if __name__ == '__main__':
	web.run_app(app, host=HOST, port=PORT)

