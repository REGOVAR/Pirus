#!python
# coding: utf-8


import os
import asyncio

from config import *
from core.framework import PirusContainerManager
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
        self.supported_features = {
            "pause_job" : True,
            "stop_job" : True,
            "monitoring_job" : False
        }

    async def install_pipeline(self, pipeline):
        """ Fake installation, success if pipeline id is odd; failed otherwise """
        await asyncio.sleep(0)
        return pipeline.id % 2 == 0

    async def uninstall_pipeline(self, pipeline):
        """ Fake uninstallation, success if pipeline id is odd; failed otherwise """
        await asyncio.sleep(0)
        return pipeline.id % 2 == 0

    def init_job(self, job):
        """ Fake init job : success if pipeline id is odd; failed otherwise """
        return job.id % 2 == 0


    def start_job(self, job):
        """ Fake start job : success if pipeline id is odd; failed otherwise """
        return job.id % 2 == 0


    def pause_job(self, job):
        """ Fake pause job : success if pipeline id is odd; failed otherwise """
        return job.id % 2 == 0


    def stop_job(self, job):
        """ Fake stop job : success if pipeline id is odd; failed otherwise """
        return job.id % 2 == 0


    async def terminate_job(self, job):
        """ Fake terminate job : success if pipeline id is odd; failed otherwise """
        await asyncio.sleep(0)
        return job.id % 2 == 0




class TestCoreFileManager(unittest.TestCase):
    """ Test case for pirus model File's features. """

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # PREPARATION
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    @classmethod
    def setUpClass(self):
        # Before test we add our fake ContainerManager in the core
        pirus.container_managers["test"] = FakeContainerManager4Test()


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
        f = pirus.files.upload_init("test_upload.tar.gz", 10, {'tags':'Coucou'})
        self.assertEqual(f.name, "test_upload.tar.gz")
        self.assertEqual(f.size, 10)
        self.assertEqual(f.upload_offset, 0)
        self.assertEqual(f.status, "uploading")
        self.assertEqual(f.type, "gz")
        self.assertEqual(f.path.startswith(TEMP_DIR), True)
        old_path = f.path

        # Upload chunk
        f = pirus.files.upload_chunk(f.id, 0, 5, b'chunk')
        self.assertEqual(f.size, 10)
        self.assertEqual(f.upload_offset, 5)
        self.assertEqual(f.status, "uploading")
        self.assertEqual(os.path.isfile(f.path),True) 
        self.assertEqual(os.path.getsize(f.path), f.upload_offset)

        # Upload finish
        f = pirus.files.upload_chunk(f.id, 5, 5, b'chunk')
        self.assertEqual(f.size, 10)
        self.assertEqual(f.upload_offset, f.size)
        self.assertEqual(f.status, "uploaded")
        self.assertEqual(f.path.startswith(FILES_DIR), True)
        self.assertEqual(os.path.isfile(old_path), False)
        self.assertEqual(os.path.isfile(f.path), True)
        self.assertEqual(os.path.getsize(f.path), f.size)

        # Install Pipe
        with open(f.path, "r") as r:
            c = r.readlines()
        self.assertEqual(c, ['chunkchunk'])

        # Delete file
        pirus.files.delete(f.id)
        f2 = File.from_id(f.id)
        self.assertEqual(f2, None)
        self.assertEqual(os.path.isfile(f.path), False)




    # def test_CRUD_image_url(self):
    #     # TODO
    #     pass



    # def test_CRUD_image_local(self):
    #     # TODO
    #     pass


