#!env/python3
# coding: utf-8
import os


from core.framework import PirusManager




class LxdManager(PirusManager):
    """
        Pirus manager to run pipeline from LXD container
    """
    def start_job(job_id):
        raise RegovarException("The abstract method \"start_job\" of PirusManager must be implemented.")


    def terminate_job(job_id):
        raise RegovarException("The abstract method \"terminate_job\" of PirusManager must be implemented.")