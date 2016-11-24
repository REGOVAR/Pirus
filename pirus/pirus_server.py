#!python
# coding: utf-8

import os



# Pirus package
from config import *



# Some check before starting the web application
if not os.path.exists(TEMPLATE_DIR):
    raise PirusException("ERROR : Templates directory doesn't exists : " + TEMPLATE_DIR)



# Init Celery
from celery import Celery
celery_app = Celery('application_worker')
celery_app.conf.update(
    BROKER_URL = 'amqp://guest@localhost',
    # CELERY_RESULT_BACKEND = 'rpc',
    # CELERY_RESULT_PERSISTENT = False,
    CELERY_TASK_SERIALIZER = 'json',
    CELERY_ACCEPT_CONTENT = ['json'],
    CELERY_RESULT_SERIALIZER = 'json',
    CELERY_INCLUDE = ['pirus_worker'],
    CELERY_TIMEZONE = 'Europe/Paris',
    CELERY_ENABLE_UTC = True,
)







# Load rest of pirus application shall be done after celery init
from aiohttp import web
from api_rest import *



# Start the pirus server
if __name__ == '__main__':
    web.run_app(app, host=HOST, port=PORT)

