# -*- coding: utf-8 -*-
"""Installation and deployment script."""

try:
    from setuptools import find_packages, setup
except ImportError:
    from distutils.core import find_packages, setup

from yand import __version__ as version


description = 'NAND flash reader/writer.'

long_description = (
    'yand is a tool to help read and write NAND flash using FT2232H devices')

setup(
    name='yand',
    version=version,
    description=description,
    long_description=long_description,
    url='https://github.com/conchyliculture/yand',
    author='Renzo',
    license='Apache License, Version 2.0',
    packages=find_packages(exclude=['cli']),
    install_requires=[
        'pyftdi',
        'tqdm',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    scripts=['cli/yand_cli.py']
)
