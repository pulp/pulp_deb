#!/usr/bin/env python3

from setuptools import setup

requirements = [
    'pulpcore-plugin>=0.1.0b17',
    'python-debian',
]

setup(
    name='pulp-deb',
    version='2.0.0a1.dev1',
    description='pulp-deb plugin for the Pulp Project',
    license='GPLv2+',
    author='Matthias Dellweg',
    author_email='dellweg@atix.de',
    url='https://pulpproject.org/#deb',
    python_requires='>=3.6',
    install_requires=requirements,
    include_package_data=True,
    packages=['pulp_deb', 'pulp_deb.app'],
    classifiers=(
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: POSIX :: Linux',
        'Framework :: Django',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ),
    entry_points={
        'pulpcore.plugin': [
            'pulp_deb = pulp_deb:default_app_config',
        ]
    }
)
