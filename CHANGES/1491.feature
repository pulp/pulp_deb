Allow `repositories/deb/apt/{pulp_id}/modify/` requests to assign added packages using the optional
`distribution` and `component` parameters. Supplying either parameter creates the corresponding
release component, release architecture, and package-release-component content; omitting both
preserves the existing package-only behavior.