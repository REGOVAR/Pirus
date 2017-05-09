#!env/python3
# coding: utf-8
import os


from core.framework import PirusManager




class CondaManager(PirusManager):
    """
        Pirus manager to run pipeline retrieved from a conda's channel
    """
    def start_job(job_id):
        raise RegovarException("The abstract method \"start_job\" of PirusManager must be implemented.")


    def terminate_job(job_id):
        raise RegovarException("The abstract method \"terminate_job\" of PirusManager must be implemented.")