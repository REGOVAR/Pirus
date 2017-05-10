#!python
# coding: utf-8


import os
import sys
import shutil
import unittest
import json
import datetime

from config import DATABASE_NAME
from core.model import *



# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# TEST PARAMETER / CONSTANTS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
TU_PIRUS_PIPELINE_PUBLIC_FIELDS = ["id", "name", "type", "status", "description", "license", "developers", "installation_date", "version", "pirus_api", "image_file_id", "image_file", "vm_settings", "ui_form", "ui_icon", "root_path", "jobs_ids", "jobs"]





class TestModelPipeline(unittest.TestCase):
    """ Test case for pirus model Pipeline's features. """

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # PREPARATION
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    @classmethod
    def setUpClass(self):
        # Before test we check that we are doing test on a "safe" database
        if DATABASE_NAME[-5:] != "_test": raise Exception("Wrong config database used")

    @classmethod
    def tearDownClass(self):
        # self.db.drop_database(DATABASE_NAME)
        # shutil.rmtree(TEMP_DIR)
        # shutil.rmtree(FILES_DIR)
        pass



    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    # TESTS
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    def test_public_fields(self):
        """ 
            Check that public fileds describes in the model are same that in TU.
            If you broke this test, you probably have to update TU, documentation and wiki...
        """
        self.assertEqual(Pipeline.public_fields, TU_PIRUS_PIPELINE_PUBLIC_FIELDS)


    def test_from_id(self):
        """ Check that requesting from id is working as expected """
        self.assertEqual(Pipeline.from_id(0), None)
        p = Pipeline.from_id(1)
        self.assertIsInstance(p, Pipeline)
        self.assertEqual(p.name, "TestPipeline 1")


    def test_from_ids(self):
        """ Check that requesting from list of id is working as expected """
        self.assertEqual(Pipeline.from_ids([]), [])
        p = Pipeline.from_ids([2,15415, 1])
        self.assertIsInstance(p, list)
        self.assertEqual(len(p), 2)
        self.assertIsInstance(p[0], Pipeline)
        self.assertIsInstance(p[1], Pipeline)
        self.assertEqual(p[0].id, 1)
        self.assertEqual(p[1].id, 2)


    def test_load_depth(self):
        """ Test that initialisation of Pipeline object with depth loading is working """
        p = Pipeline.from_id(1, 1)
        self.assertIsInstance(p.image_file, File)
        self.assertEqual(p.image_file.id, 1)


    def test_to_json(self):
        """ Test export to json """
        # Test export with default fields
        p = Pipeline.from_id(1, 1)
        j = p.to_json()
        self.assertEqual(len(j), 14)
        json.dumps(j)

        # Test export with only requested fields
        j = p.to_json(["id", "ui_form", "status", "jobs_ids"])
        self.assertEqual(len(j), 4)
        json.dumps(j)

        # Test export with depth loading
        j = p.to_json(["id", "ui_form", "status", "jobs"])
        self.assertEqual(len(j), 4)
        self.assertEqual(j["jobs"][0]["id"], 1)
        self.assertEqual(j["jobs"][1]["progress_value"], 0.5)


    def test_CRUD(self):
        """ Test creation of a new file object, update, read and delete """
        # CREATE
        total = Pipeline.count()
        p1 = Pipeline.new()
        self.assertEqual(Pipeline.count(), total + 1)
        self.assertNotEqual(p1.id, None)
        # UPDATE
        p1.name = "TestPipeline"
        p1.save()
        # READ
        p2 = Pipeline.from_id(p1.id)
        self.assertEqual(p2.name, "TestPipeline")
        self.assertEqual(p2.installation_date, p1.installation_date)
        # UPDATE loading
        v = datetime.datetime.now().ctime()
        p2.load({
            "name" : "FinalPipeline", 
            "type" : "lxd", 
            "status" : "ready",
            "description" : "Pipeline Description",
            "license" : "AGPL8",
            "developers" : "['Tata', 'Titi']",
            "version" : v,
            "pirus_api" : "v1",
            "image_file_id" : 1,
            "vm_settings" : '{"param1" : 1, "param2" : [1,2,3]}',
            "ui_form" : '{"param1" : 1, "param2" : [1,2,3]}'
            })
        self.assertEqual(p2.name,"FinalPipeline")
        self.assertEqual(p2.type,"lxd")
        self.assertEqual(p2.status,"ready")
        self.assertEqual(p2.description,"Pipeline Description")
        self.assertEqual(p2.license,"AGPL8")
        self.assertEqual(p2.developers,"['Tata', 'Titi']")
        self.assertEqual(p2.version, v)
        self.assertEqual(p2.pirus_api,"v1")
        self.assertEqual(p2.image_file_id,1)
        configjson = json.loads(p2.vm_settings)
        self.assertEqual(configjson["param2"][1], 2)
        self.assertEqual(p2.ui_form,'{"param1" : 1, "param2" : [1,2,3]}')
        # READ
        p3 = Pipeline.from_id(p1.id, 1)
        self.assertEqual(p3.status,"ready")
        self.assertEqual(p3.image_file_id, 1)
        # DELETE
        Pipeline.delete(p3.id)
        p4 = Pipeline.from_id(p3.id)
        self.assertEqual(p4, None)
        self.assertEqual(Pipeline.count(), total)