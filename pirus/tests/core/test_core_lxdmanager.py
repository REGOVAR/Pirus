#!python
# coding: utf-8

import ipdb

import os
import sys
import shutil
import unittest
import subprocess
import yaml
import time

from config import *
from core.model import File, Pipeline
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

    def test_000_pipeline_image_installation(self):
        """ Check that installation of the PirusSimpleContainer from local image file is working. """

        # install the fake pipeline
        p = pirus.pipelines.install_init_image_local(self.IMAGE_FILE_PATH, move=False, metadata={"type" : "lxd"})
        pirus.pipelines.install(p.id, asynch=False)
        TestCoreLxdManager.pid = p.id

        # waiting = self.MAX_WAITING_4_INSTALL
        # success = False
        # while waiting > 0:
        #     time.sleep(1)
        #     waiting -= 1
        #     if Pipeline.from_id(TestCoreLxdManager.pid).status == "ready":
        #         break;

        p = Pipeline.from_id(TestCoreLxdManager.pid, 1)
        self.assertEqual(p.status, "ready")
        self.assertEqual(os.path.isfile(self.IMAGE_FILE_PATH), True)
        self.assertNotEqual(self.IMAGE_FILE_PATH, p.image_file.path)



    def test_100_job_CRUD_normal_workflow(self):
        """ Check lxd job's normal worklow (without errors) """

        # job creation


        # job start


        # job monotoring


        # job pause


        # job monotoring



        # job start


        # job stop

        pass







    def test_900_pipeline_image_deletion(self):
        # uninstall the pipeline
        p0 = Pipeline.from_id(TestCoreLxdManager.pid)
        pirus.pipelines.delete(p0.id, False)  # delete it synchronously to be able to test correctly

        # check that image file no more exists
        self.assertEqual(os.path.isfile(p0.image_file.path), False)
        f = File.from_id(p0.image_file_id)
        self.assertEqual(f, None)

        # check that pipeline no more exists
        self.assertEqual(os.path.exists(p0.root_path), False)
        p1 = Pipeline.from_id(p0.id)
        self.assertEqual(p1, None)

        # check that lxd image no more exists
        lxd_alias = yaml.load(p0.vm_settings)["lxd_alias"]
        out_tmp = '/tmp/test_out'
        self.assertEqual(subprocess.call(["lxc", "image", "list"], stdout=open(out_tmp, "w")), 0)
        out = open(out_tmp, "r").read()
        self.assertEqual(lxd_alias in out, False)



