# Client Bindings

## Python Client

The [pulp-deb-client package](https://pypi.org/project/pulp-deb-client/) on PyPI provides bindings for all `pulp_deb` [REST API][1] endpoints.
It is currently published daily and with every RC.

The [pulpcore-client package](https://pypi.org/project/pulpcore-client) on PyPI provides bindings for all `pulpcore` [REST API][2] endpoints.
It is currently published daily and with every RC.

## Ruby Client

The [pulp_deb_client Ruby Gem](https://rubygems.org/gems/pulp_deb_client) on rubygems.org provides bindings for all `pulp_deb` [REST API][1] endpoints.
It is currently published daily and with every RC.

The [pulpcore_client Ruby Gem](https://rubygems.org/gems/pulpcore_client) on rubygems.org provides bindings for all `pulpcore` [REST API][2] endpoints.
It is currently published daily and with every RC.

## Client in a Language of Your Choice

A client can be generated using Pulp's OpenAPI schema and any of the available [OpenAPI generators](https://openapi-generator.tech/docs/generators).

Generating a client is a two step process:

1. Download the OpenAPI schema for pulpcore and all installed plugins:
   ```bash
   curl -o api.json http://<pulp-hostname>:24817/pulp/api/v3/docs/api.json
   ```
   The OpenAPI schema for a specific plugin can be downloaded by specifying the plugin's module name as a GET parameter.
   For example for `pulp_deb` only endpoints use a query like this:
   ```bash
   curl -o api.json http://<pulp-hostname>:24817/pulp/api/v3/docs/api.json?plugin=pulp_deb
   ```
2. Generate a client using OpenAPI generator:
   The schema can then be used as input to the `openapi-generator-cli`.
   See [try OpenAPI generator](https://openapi-generator.tech/#try) for documentation on getting started.

[1]: https://staging-docs.pulpproject.org/pulp_deb/restapi/
[2]: https://staging-docs.pulpproject.org/pulpcore/restapi/
