#!/usr/bin/env python
# Copyright 2013-2018 Netflix, Inc.

from setuptools import setup, find_packages
from pip.req import parse_requirements
from pip.download import PipSession

setup(
    name = 'cligraphy',
    version = '0.0.7',
    description = 'Cligraphy Command line tools',
    long_description = 'Cligraphy Command line tools',
    author = 'Netflix, Inc.',
    author_email = '',  # OPEN SOURCE TODO
    packages = find_packages(),
    include_package_data=True,
    license='Apache 2.0',
    zip_safe=False,
    install_requires = [str(ir.req) for ir in parse_requirements('requirements.txt', session=PipSession())],
)
