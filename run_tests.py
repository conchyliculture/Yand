"""Run all tests inside the tests folder."""
import glob
import unittest
import sys

from pylint.lint import Run


loader = unittest.TestLoader()
suite = loader.discover('yand', pattern='*_tests.py')

runner = unittest.TextTestRunner()
result = runner.run(suite)

Run(['--rcfile', '.pylintrc', 'yand'] +
    glob.glob('*.py') +
    glob.glob('cli/*.py') +
    glob.glob('tools/*.py'), do_exit=True)

sys.exit(not result.wasSuccessful())
