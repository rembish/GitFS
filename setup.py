#!/usr/bin/env python
try:
    from debian.changelog import Changelog
except ImportError:
    class Changelog(object):
        version = "Unknown"

        def __init__(self, _):
            pass

from os.path import abspath, join, dirname
from setuptools import setup, find_packages

here = abspath(dirname(__file__))
requirements = open(join(here, 'requires.txt')).readlines()
changelog = open(join(here, 'debian/changelog'))

setup(
    name='gitfs',
    version=str(Changelog(changelog).version),
    packages=find_packages(),
    install_requires=requirements,
    author='Alex Rembish',
    author_email='alex@rembish.org'
)

