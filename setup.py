#!/usr/bin/env python

description = '''\
txretry provides a Twisted class, RetryingCall, that calls a function
until it succeeds. A back-off iterator (a generator function that yields
intervals) can be specified to customize the interval between retried
calls.  When/if the back-off iterator raises StopIteration the attempt to
call the function is aborted. An instance of the RetryingCall class
provides a start method that returns a Deferred that will fire with the
function result or errback with the first failure encountered.

Usage of the class is described in the following blog post:
http://blogs.fluidinfo.com/terry/2009/11/12/twisted-code-for-retrying-function-calls/
'''

d = dict(name='txretry',
         version='1.0.0',
         provides=['txretry'],
         maintainer='Fluidinfo Inc.',
         maintainer_email='terry@jon.es',
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
         description=('A Twisted class for retrying failing calls '
                      'with a customizable back-off schedule.'),
         long_description=description,
         )

try:
    from setuptools import setup
    _ = setup  # Keeps pyflakes from complaining.
except ImportError:
    from distutils.core import setup
else:
    d['install_requires'] = ['Twisted', 'six']

setup(**d)
