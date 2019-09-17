"""Run all tests inside the tests folder."""
import unittest
import sys


loader = unittest.TestLoader()
suite = loader.discover('yand', pattern='*_tests.py')

runner = unittest.TextTestRunner()
result = runner.run(suite)
#sys.exit(not result.wasSuccessful())
