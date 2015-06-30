from setuptools import setup, find_packages

setup(
    name='pulp_deb_extensions_admin',
    version='1.0.0b3',
    packages=find_packages(),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='pulp-admin extensions for deb support',
    entry_points={
        'pulp.extensions.admin': [
            'repo_admin = pulp_deb.extensions.admin.pulp_cli:initialize',
        ]
    }
)
