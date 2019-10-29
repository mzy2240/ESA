#!/usr/bin/env python
import setuptools

with open("ReadMe.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name = 'esa',
    version = '0.4.0',
    description = 'A python package that makes PowerWorld Simauto easier yet more powerful to use',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author = 'Zeyu Mao, Brandon Thayer',
    author_email = 'zeyumao2@tamu.edu, blthayer@tamu.edu',
    url = 'https://github.com/mzy2240/ESA',
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=['paho-mqtt', 'tqdm', 'psutil', 'pandas', 'numpy', 'pywin32', 'pypiwin32'],
    license='MIT',
    zip_safe=False
)
