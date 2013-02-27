#!/usr/bin/env python

import os


# Utility function to read the README file.
# Credit: http://pypi.python.org/pypi/an_example_pypi_project
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

d = dict(name='txretry',
         version='0.0.2',
         provides=['txretry'],
         maintainer='Fluidinfo Inc.',
         maintainer_email='info@fluidinfo.com',
         url='https://github.com/fluidinfo/txretry',
         download_url='https://github.com/fluidinfo/txretry',
         packages=['txretry', 'txretry.test'],
         keywords=['twisted function retry'],
         classifiers=[
             'Programming Language :: Python',
             'Framework :: Twisted',
             'Development Status :: 4 - Beta',
             'Intended Audience :: Developers',
             'License :: OSI Approved :: Apache Software License',
             'Operating System :: OS Independent',
             'Topic :: Software Development :: Libraries :: Python Modules',
             ],
         description=('A Twisted class for retrying failed calls '
                      'with a customizable back-off schedule.'),
         long_description=read('README'),
         )

try:
    from setuptools import setup
    _ = setup  # Keeps pyflakes from complaining.
except ImportError:
    from distutils.core import setup
else:
    d['install_requires'] = ['Twisted']

setup(**d)
