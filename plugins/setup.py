from setuptools import setup, find_packages

setup(
    name='pulp_deb_plugins',
    version='1.10.1',
    packages=find_packages(exclude=['test', 'test.*']),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='plugins for deb support in pulp',
    entry_points={
        'pulp.importers': [
            'importer = pulp_deb.plugins.importers.importer:entry_point',
        ],
        'pulp.distributors': [
            'distributor = pulp_deb.plugins.distributors.distributor:entry_point'  # noqa
        ],
        'pulp.server.db.migrations': [
            'pulp_deb = pulp_deb.plugins.migrations',
        ],
        'pulp.unit_models': [
            'deb=pulp_deb.plugins.db.models:DebPackage',
            'deb_release=pulp_deb.plugins.db.models:DebRelease',
            'deb_component=pulp_deb.plugins.db.models:DebComponent',
        ],
    },
    include_package_data=True,
    data_files=[
        ('/etc/httpd/conf.d', ['etc/httpd/conf.d/pulp_deb.conf']),
    ],
    install_requires=[
        'python-gnupg',
    ],
)
