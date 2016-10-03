#!env/python3
# coding: utf-8


import aiohttp
import aiohttp_jinja2
import jinja2


from aiohttp import web
from config import *


# Common tools

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







# Create server app
app = web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(TEMPLATE_DIR))
