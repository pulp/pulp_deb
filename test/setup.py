from setuptools import setup, find_packages

setup(
    name='pulp_deb_test',
    version='1.1.0a1',
    packages=find_packages(),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='package to force installation of certain libraries needed for testing',
    install_requires=[
        'appdirs>=1.4.3',
        'packaging>=16.8', 'pip>=9.0.1', 'pyparsing>=2.2',
        'six>=1.10'],
)
