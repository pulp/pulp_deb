## How to add new test data for functional tests.

- To add new data you need to create a debian repository including `.deb` packages and meta data. You can create them yourself from scratch or use tools (e.g. `equivs-build`, `reprepro`, etc) to generate them from config files.
- Put your files here `pulp_deb/tests/functional/data/`.
- To use your data in a test make sure to call this pytest fixture `deb_remote_factory()` with the following parameter: `repo_name=NAME_OF_YOUR_DATA_REPO`.

### Misc

- Scripts of some of the available test data can be found: https://github.com/pulp/pulp-fixtures/tree/master/debian
