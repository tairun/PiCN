#!/usr/bin/env python3.6

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config_PyNDN = {
    'description': 'PyNDN',
    'author': 'UCLA, Jeff Thompson',
    'url': 'https://github.com/cn-uofbasel/PiCN',
    'download_url': '',
    'author_email': 'jefft0@remap.ucla.edu',
    'version': '2',
    'license': 'GNU LESSER GENERAL PUBLIC LICENSE, Version 3, 29 June 2007',
    'platforms': ['UNIX', 'POSIX', 'BSD', 'MacOS 10.X', 'Linux'],
    'description': 'PyNDN Packet encoder',
    'long_description': 'PyNDN Packet encoder for the NDN packet format',
    'install_requires': [],
    'packages': ['pyndn'],
    'scripts': [],
    'name': 'pyndn'
}
setup(**config_PyNDN)
