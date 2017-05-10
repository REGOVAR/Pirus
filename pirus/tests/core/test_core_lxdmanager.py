#!python
# coding: utf-8


import os
import sys
import shutil
import unittest
import json
import time

from config import *
from core.model import Pipeline
from core.core import pirus


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# TEST PARAMETER / CONSTANTS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #




class TestCoreLxdManager(unittest.TestCase):
    """ Test case for lxd container management. """

    IMAGE_FILE_PATH = "/var/regovar/pirus/_pipes/PirusSimple.tar.xz"
    MAX_WAITING_4_INSTALL = 60 # 60s (actually, installing PirusSimple need ~45s)



    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # PREPARATION
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    @classmethod
    def setUpClass(self):
        pass
        

    @classmethod
    def tearDownClass(self):
        pass



    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # TESTS
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    def test_pipeline_image_installation(self):
        """ Check that installation of the PirusSimpleContainer from local image file is working. """

        # install the fake pipeline
        p = pirus.pipelines.install_init_image_local(self.IMAGE_FILE_PATH, metadata={"type" : "lxd"})
        pirus.pipelines.install(p.id)
        self.pid = p.id

        waiting = self.MAX_WAITING_4_INSTALL
        success = False
        while waiting > 0:
            time.sleep(1)
            waiting -= 1
            if Pipeline.from_id(self.pid).status == "ready":
                break;


        p = Pipeline.from_id(self.pid)
        self.assertEqual(p.status, "ready")


        # uninstall the fake pipeline
        # pirus.pipelines.delete(p.id)

        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_init, False)
        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_running, False)
        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_monitoring, False)
        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_paused, False)
        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_stoped, False)
        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_monitoring, False)
        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_finalized, False)


        # # init job 
        # time.sleep(0.1) # need waiting otherwise sqlalchemy in wrong state ?... to fixe
        # job = pirus.jobs.new(p.id, {"name" : "Test job success"})
        # job_id = job.id
        # root_path =  os.path.join(JOBS_DIR, "{}_{}".format(job.pipeline_id, job.id))
        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_init, True)
        # self.assertEqual(job.name, "Test job success")
        # self.assertEqual(os.path.exists(root_path), True)
        # self.assertEqual(os.path.exists(os.path.join(root_path, "inputs")), True)
        # self.assertEqual(os.path.exists(os.path.join(root_path, "outputs")), True)
        # self.assertEqual(os.path.exists(os.path.join(root_path, "logs")), True)
        # self.assertEqual(os.path.isfile(os.path.join(root_path, "inputs/config.json")), True)

        # # call all delayed action 
        # pirus.jobs.start(job_id)
        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_running, True)

        # job = pirus.jobs.monitoring(job_id)
        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_monitoring, True)

        # pirus.jobs.pause(job_id)
        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_paused, True)

        # pirus.jobs.start(job_id)
        # pirus.jobs.stop(job_id)
        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_stoped, True)

        # pirus.jobs.finalize(job_id)
        # self.assertEqual(pirus.container_managers["FakeManager4Test"].is_finalized, True)

        # pirus.jobs.delete(job_id)
        # self.assertEqual(os.path.isfile(os.path.join(root_path, "inputs/config.json")), False)
        # self.assertEqual(os.path.exists(os.path.join(root_path, "inputs")), False)
        # self.assertEqual(os.path.exists(os.path.join(root_path, "outputs")), False)
        # self.assertEqual(os.path.exists(os.path.join(root_path, "logs")), False)
        # self.assertEqual(os.path.exists(root_path), False)




    def test_job_container_creation (self):

        # init job 

        # start job

        # check error

        # check that terminate job have been automaticaly called by the manager 

        # check i/o files of the job
        pass



