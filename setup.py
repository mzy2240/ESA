#!/usr/bin/env python

from setuptools import setup

setup(
    name = 'ssimauto',
    version = '0.2',
    description = 'A python package that makes PowerWorld Simauto easier yet more powerful to use',
    long_description = open('README.rst').read() + '\n\n' + open('HISTORY.rst').read(),
    author = 'Zeyu Mao',
    author_email = 'zeyumao2@tamu.edu',
    url = 'https://github.tamu.edu/zeyumao2/ssimauto',
    packages = [
        'ssimauto'
    ],
    install_requires=['paho-mqtt', 'tqdm', 'psutil', 'pandas', 'numpy', 'pywin32', 'pypiwin32', ],
    license='MIT',
    zip_safe=False
)
