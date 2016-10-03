#!env/python3
# coding: utf-8

import os
import json
import aiohttp
import aiohttp_jinja2
import jinja2
import zipfile
import shutil
import datetime
import time
import uuid

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
if not os.path.exists(RUN_DIR):
	os.makedirs(RUN_DIR)
if not os.path.exists(PIPELINES_DIR):
	os.makedirs(PIPELINES_DIR)
if not os.path.exists(TEMPLATE_DIR):
	print("ERROR : Templates directory doesn't exists.", TEMPLATE_DIR)



# Start the pirus server
if __name__ == '__main__':
	web.run_app(app)

