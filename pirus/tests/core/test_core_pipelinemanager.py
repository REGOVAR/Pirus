#!python
# coding: utf-8


import os
import unittest
import asyncio
import time

from config import *
from core.framework import PirusContainerManager, run_until_complete
from core.model import File, Pipeline
from core.core import pirus



# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# TEST PARAMETER / CONSTANTS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #



class FakeContainerManager4Test(PirusContainerManager):
    """
        This test will check that workflow between core, container manager and celery are working as expected.
        This test will not check container managers.
        Note that there are dedicated tests by container manager's type (lxd, github, ...)
    """
    def __init__(self):
        self.need_image_file = True
        self.supported_features = {
            "pause_job" : True,
            "stop_job" : True,
            "monitoring_job" : False
        }
        self.is_installed = False


    def install_pipeline(self, pipeline):
        """ Fake installation, success if pipeline's name contains "success"; failed otherwise """
        self.is_installed = "success" in pipeline.name
        return self.is_installed

    def uninstall_pipeline(self, pipeline):
        """ Fake uninstallation, success if pipeline's name contains "success"; failed otherwise """
        self.is_installed = "success" in pipeline.name
        return self.is_installed

    def init_job(self, job):
        """ Fake init job : success if job's name contains "success"; failed otherwise """
        return "success" in job.name


    def start_job(self, job):
        """ Fake start job : success if job's name contains "success"; failed otherwise """
        return "success" in job.name


    def pause_job(self, job):
        """ Fake pause job : success if job's name contains "success"; failed otherwise """
        return "success" in job.name


    def stop_job(self, job):
        """ Fake stop job : success if job's name contains "success"; failed otherwise """
        return "success" in job.name


    def terminate_job(self, job):
        """ Fake terminate job : success if job's name contains "success"; failed otherwise """
        return "success" in job.name




class TestCorePipelineManager(unittest.TestCase):
    """ Test case for pirus model File's features. """

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # PREPARATION
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    @classmethod
    def setUpClass(self):
        # Before test we add our fake ContainerManager in the core
        pirus.container_managers["FakeManager4Test"] = FakeContainerManager4Test()


    @classmethod
    def tearDownClass(self):
        # self.db.drop_database(DATABASE_NAME)
        # shutil.rmtree(TEMP_DIR)
        # shutil.rmtree(FILES_DIR)
        pass



    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # TESTS
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    def test_CRUD_image_upload(self):
        """ Check that upload's features are working as expected """

        # Upload init
        p, f = pirus.pipelines.install_init_image_upload("test_image_success.tar.gz", 10, {"type" : "FakeManager4Test"})
        self.assertEqual(f.name, "test_image_success.tar.gz")
        self.assertEqual(f.size, 10)
        self.assertEqual(f.upload_offset, 0)
        self.assertEqual(f.status, "uploading")
        self.assertEqual(f.path.startswith(TEMP_DIR), True)
        self.assertEqual(p.name, f.name)
        self.assertEqual(p.status, "initializing")
        self.assertEqual(p.type, "FakeManager4Test")
        self.assertEqual(p.image_file_id, f.id)

        old_path = f.path

        # Upload chunk
        f = pirus.files.upload_chunk(f.id, 0, 5, b'chunk')
        self.assertEqual(f.size, 10)
        self.assertEqual(f.upload_offset, 5)
        self.assertEqual(f.status, "uploading")
        self.assertEqual(p.status, "initializing")
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_installed, False)

        # Upload finish -> installation shall start automatically as the type have been set
        f = pirus.files.upload_chunk(f.id, 5, 5, b'chunk')
        self.assertEqual(f.size, 10)
        self.assertEqual(f.upload_offset, f.size)
        self.assertEqual(f.status, "uploaded")
        self.assertEqual(f.path.startswith(FILES_DIR), True)
        self.assertEqual(os.path.isfile(old_path), False)
        self.assertEqual(os.path.isfile(f.path), True)
        self.assertEqual(os.path.getsize(f.path), f.size)

        time.sleep(0.1) # Wait that other thread call for the install ends

        # Check that install_pipeline method have been successfully called
        p = Pipeline.from_id(p.id)
        self.assertEqual(pirus.container_managers["FakeManager4Test"].is_installed, True)
        self.assertEqual(p.status, "ready")

        # Delete pipeline
        path = f.path
        r = pirus.pipelines.delete(p)
        self.assertEqual(r, True)
        self.assertEqual(Pipeline.from_id(p.id), None)
        self.assertEqual(File.from_id(p.image_file_id), None)
        self.assertEqual(os.path.isfile(path), False)




    # def test_CRUD_image_url(self):
    #     # TODO
    #     pass



    # def test_CRUD_image_local(self):
    #     # TODO
    #     pass


