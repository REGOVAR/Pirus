#!python
# coding: utf-8

import os
from aiohttp import web


# Pirus package
from api_rest import *


# Some check before starting the web application
if not os.path.exists(TEMPLATE_DIR):
    raise PirusException("ERROR : Templates directory doesn't exists : " + TEMPLATE_DIR)



# Start the pirus server
if __name__ == '__main__':
	web.run_app(app, host=HOST, port=PORT)

