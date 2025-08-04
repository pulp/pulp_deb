from pulpcore.plugin import PulpPluginAppConfig


class PulpDebPluginAppConfig(PulpPluginAppConfig):
    """Entry point for the deb plugin."""

    name = "pulp_deb.app"
    label = "deb"
    version = "3.6.1.dev"
    python_package_name = "pulp_deb"
    domain_compatible = True
