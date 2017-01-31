#!/usr/bin/env python
# (C) Netflix 2014

"""Lint command tests
"""

from nflx_oc.commands.dev import lint

import os

import unittest


class TestModuleDiscovery(unittest.TestCase):
    """"""

    def setUp(self):
        self.test_data_root = os.path.join(os.path.dirname(lint.__file__), 'testdata/lint')
        self.prevdir = os.getcwd()
        os.chdir(self.test_data_root)

    def tearDown(self):
        os.chdir(self.prevdir)

    def test_module_discovery(self):
        """Test our lint wrapper module discovery
        """
        self.assertEqual(lint.find_python_modules('package'), ['package'])
        self.assertEqual(lint.find_python_modules('two-modules'), ['two-modules/a', 'two-modules/b'])
        self.assertEqual(lint.find_python_modules('two-modules-and-one-nested'),
                         ['two-modules-and-one-nested/a', 'two-modules-and-one-nested/b', 'two-modules-and-one-nested/d/d2'])
