#!/usr/bin/env python
from distutils.core import setup
import py2exe
import sys
import os
import yaml

DIST_PATH = r'bin'

sys.argv = [sys.argv[0],]
sys.argv += ['py2exe','--dist-dir',DIST_PATH]

setup(
    #console=['serie.py'],
    windows=['serie.py'],
    options={
        'py2exe' : {
        'includes' : [
            # 'zope.interface',
            # 'yaml',
            ]
        },
        },
    )
