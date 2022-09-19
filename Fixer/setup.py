# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import setuptools 
from os import path

name = "fixer"
author = "SupraCoNeX"
version = "0.0.1"
release = ".".join(version.split(".")[:2])

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name=name,
    version="0.0.1",
    author=author,
    author_email="supraconex@supraconex.org",
    description="Rate Control via Fixed Rate Setting",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/supraconex.org",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[],
)
