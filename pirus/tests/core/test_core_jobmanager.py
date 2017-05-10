#!python
# coding: utf-8


import os
import sys
import shutil
import unittest
import json
import time

from config import *
from core.model import File
from core.core import pirus


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# TEST PARAMETER / CONSTANTS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #




class TestCoreJobManager(unittest.TestCase):
    """ Test case for pirus model File's features. """

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # PREPARATION
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    @classmethod
    def setUpClass(self):
        pirus.container_managers["FakeManager4Test"].need_image_file = False

    @classmethod
    def tearDownClass(self):
        # self.db.drop_database(DATABASE_NAME)
        # shutil.rmtree(TEMP_DIR)
        # shutil.rmtree(FILES_DIR)
        pass



    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # TESTS
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    def test_main_workflow_without_error(self):
        """ Check that job core's workflow, for job, is working as expected. """

        # install the fake pipeline
        p = pirus.pipelines.install_init("test_image_success", {"type" : "FakeManager4Test"})
        pirus.pipelines.install(p.id, asynch=False)

        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_init, False)
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_running, False)
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_monitoring, False)
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_paused, False)
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_stoped, False)
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_monitoring, False)
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_finalized, False)


        # init job 
        #time.sleep(0.1) # need waiting otherwise sqlalchemy in wrong state ?... to fixe
        job = pirus.jobs.new(p.id, {"name" : "Test job success"}, asynch=False)
        job_id = job.id
        root_path =  os.path.join(JOBS_DIR, "{}_{}".format(job.pipeline_id, job.id))
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_init, True)
        self.assertEqual(job.name, "Test job success")
        self.assertEqual(os.path.exists(root_path), True)
        self.assertEqual(os.path.exists(os.path.join(root_path, "inputs")), True)
        self.assertEqual(os.path.exists(os.path.join(root_path, "outputs")), True)
        self.assertEqual(os.path.exists(os.path.join(root_path, "logs")), True)
        self.assertEqual(os.path.isfile(os.path.join(root_path, "inputs/config.json")), True)

        # call all delayed action 
        pirus.jobs.start(job_id, asynch=False)
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_running, True)

        job = pirus.jobs.monitoring(job_id, asynch=False)
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_monitoring, True)

        pirus.jobs.pause(job_id, asynch=False)
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_paused, True)

        pirus.jobs.start(job_id, asynch=False)
        pirus.jobs.stop(job_id, asynch=False)
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_stoped, True)

        pirus.jobs.finalize(job_id, asynch=False)
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_finalized, True)

        pirus.jobs.delete(job_id, asynch=False)
        self.assertEqual(os.path.isfile(os.path.join(root_path, "inputs/config.json")), False)
        self.assertEqual(os.path.exists(os.path.join(root_path, "inputs")), False)
        self.assertEqual(os.path.exists(os.path.join(root_path, "outputs")), False)
        self.assertEqual(os.path.exists(os.path.join(root_path, "logs")), False)
        self.assertEqual(os.path.exists(root_path), False)




    def test_main_workflow_with_error(self):

        # init job 

        # start job

        # check error

        # check that terminate job have been automaticaly called by the manager 

        # check i/o files of the job
        pass



