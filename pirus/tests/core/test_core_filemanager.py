#!python
# coding: utf-8


import os
import unittest

from config import *
from core.model import File
from core.core import pirus



# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# TEST PARAMETER / CONSTANTS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #




class TestCoreFileManager(unittest.TestCase):
    """ Test case for pirus model File's features. """

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # PREPARATION
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    @classmethod
    def setUpClass(self):
        # Before test we check that we are doing test on a "safe" database
        pass

    @classmethod
    def tearDownClass(self):
        # self.db.drop_database(DATABASE_NAME)
        # shutil.rmtree(TEMP_DIR)
        # shutil.rmtree(FILES_DIR)
        pass



    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # TESTS
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    def test_CRUD_upload(self):
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

        # Check file content
        with open(f.path, "r") as r:
            c = r.readlines()
        self.assertEqual(c, ['chunkchunk'])

        # Delete file
        pirus.files.delete(f.id)
        f2 = File.from_id(f.id)
        self.assertEqual(f2, None)
        self.assertEqual(os.path.isfile(f.path), False)




    # def test_CRUD_from_url(self):
    #     """ Check that creating file by retrieving it through url is working as expected """

    #     # TODO
    #     pass



    # def test_CRUD_from_ids(self):
    #     """ Check that creating file by retrieving it on a local path on the server is working as expected """

    #     # TODO
    #     pass


