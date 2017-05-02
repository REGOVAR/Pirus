#!env/python3
# coding: utf-8
import os


from core.framework import PirusManager




class GithubManager(PirusManager):
    """
        Pirus manager to run pipeline that are describe/define in a github repository
    """
    def start_job(job_id):
        raise RegovarException("The abstract method \"start_job\" of PirusManager must be implemented.")


    def terminate_job(job_id):
        raise RegovarException("The abstract method \"terminate_job\" of PirusManager must be implemented.")