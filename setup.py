#!/usr/bin/env python3

from setuptools import find_packages, setup

requirements = [
    'pulpcore-plugin',
]

setup(
    name='pulp-deb',
    version='0.0.1a1.dev1',
    description='pulp-deb plugin for the Pulp Project',
    license='GPLv2+',
    author='AUTHOR',
    author_email='author@email.here',
    url='http://example.com/',
    python_requires='>=3.6',
    install_requires=requirements,
    include_package_data=True,
    packages=find_packages(exclude=['tests', 'tests.*']),
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
