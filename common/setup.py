from setuptools import setup, find_packages

setup(
    name='pulp_deb_common',
    version='1.10.1',
    packages=find_packages(),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='common code for pulp\'s deb support',
)
