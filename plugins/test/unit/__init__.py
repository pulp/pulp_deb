from pulp.devel.unit.server.base import block_load_conf

# prevent attempts to load the server conf during testing
block_load_conf()
