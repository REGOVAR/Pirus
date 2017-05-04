#!python
# coding: utf-8

import unittest


from tests.model.test_model_file import TestModelFile
from tests.model.test_model_job import TestModelJob
from tests.model.test_model_pipeline import TestModelPipeline
from tests.core.test_core_filemanager import TestCoreFileManager





# /!\ For a weird raison, unittest.main() doesn't work (no UT loaded) when we import the pirus.core object. So we run the tests manually

# Run tests
if __name__ == '__main__':
    suite = unittest.TestSuite()

    # Load test to execute
    for test in [m for m in TestModelFile.__dict__.keys() if str.startswith(m, "test_")]:
        suite.addTest(TestModelFile(test))

    for test in [m for m in TestModelJob.__dict__.keys() if str.startswith(m, "test_")]:
        suite.addTest(TestModelJob(test))

    for test in [m for m in TestModelPipeline.__dict__.keys() if str.startswith(m, "test_")]:
        suite.addTest(TestModelPipeline(test))

    for test in [m for m in TestCoreFileManager.__dict__.keys() if str.startswith(m, "test_")]:
        suite.addTest(TestCoreFileManager(test))

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)