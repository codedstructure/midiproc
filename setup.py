#!/usr/bin/python

try:
    # this is primarily to support the 'develop' target
    # if setuptools/distribute are installed
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name="midiproc",
    version="0.1",
    description="coroutine-based MIDI processing package",
    long_description=open('README.rst').read(),
    author="Ben Bass",
    author_email="benbass@codedstructure.net",
    url="http://bitbucket.org/codedstructure/midiproc",
    packages=["midiproc", "midiproc.examples"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Topic :: Multimedia :: Sound/Audio :: MIDI",
    ]
)
