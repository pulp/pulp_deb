#!/usr/bin/env python3

from setuptools import find_packages, setup

with open("requirements.txt") as requirements:
    requirements = requirements.readlines()

with open("README.md") as description:
    long_description = description.read()

setup(
    name="pulp-deb",
    version="2.18.3.dev",
    description="pulp-deb plugin for the Pulp Project",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GPLv2+",
    author="Matthias Dellweg",
    author_email="dellweg@atix.de",
    url="https://pulpproject.org",
    python_requires=">=3.8",
    install_requires=requirements,
    include_package_data=True,
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=(
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 5 - Production/Stable",
        "Framework :: Django",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ),
    entry_points={"pulpcore.plugin": ["pulp_deb = pulp_deb:default_app_config"]},
)
