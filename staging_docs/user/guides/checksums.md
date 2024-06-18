# Configuring Checksums

What checksum algorithems are available on any given Pulp instance, is controlled by the pulpcore `ALLOWED_CONTENT_CHECKSUMS` setting. If enabled, `pulp_deb` will make use of MD5, SHA-1, SHA-256, and SHA-512. SHA-256 is required and cannot be disabled.

!!! important
    For compliance reasons, MD5 and SHA-1 have been disabled by default since pulpcore 3.11.

!!! note
    It is almost universal practice within the Debian ecosystem to make use of MD5 in particular.
    If your Pulp instance is configured to disallow the MD5 checksum algorithm, `pulp_deb` will log a warning with every sync as well as every use of the APT publisher.
    You can disable these warnings, by changing the `FORBIDDEN_CHECKSUM_WARNINGS` setting to `False`.


!!! warning
    While the APT publisher respects the `ALLOWED_CONTENT_CHECKSUMS` setting, the verbatim publisher will mirror an exact copy of the synced upstream metadata.
    By its very nature, the verbatim publisher  does not respect the `ALLOWED_CONTENT_CHECKSUMS` setting.
    If your policy prohibits the presence of certain checksum types, either do not use the verbatim publisher, or only synchronize repositories that are already compliant with your policy.


## Enabling MD5 and/or SHA1

In order to opt in to MD5 and/or SHA1, the values `md5` and/or `sha1` must be added to the list configured for the `ALLOWED_CONTENT_CHECKSUMS` setting. In addition a `pulpcore-manager` command must be run to generate any missing checksums within the DB for the settings change to take effect.

See the [pulpcore configuration documentation](https://staging-docs.pulpproject.org/pulpcore/docs/admin/guides/configure-pulp/) for more information on how to apply settings. Look for the section on `ALLOWED_CONTENT_CHECKSUMS` in the [pulpcore settings documentation](https://staging-docs.pulpproject.org/pulpcore/docs/admin/learn/settings/#pulp-settings) in particular.

Once you have updated your configuration file you will need to halt your Pulp instance, and then run the following command to ensure your DB is made consistent with your `ALLOWED_CONTENT_CHECKSUMS` setting:

```none
pulpcore-manager handle-artifact-checksums
```

!!! note
    Missing checksums will need to be recalculated for all your artifacts which can take some time.
    If you have a missmatch between your configured `ALLOWED_CONTENT_CHECKSUMS` setting and the checksums present in the DB, Pulp will simply refuse to start.


## Security Implications

APT repository metadata files (release files and package indecies) will typically include several checksums for all referenced files.
During synchronization, `pulp_deb` will check the downloaded files against the provided checksums.
Together with a valid (and trusted) release file signature this will guarantee the integrity of the synchronized repository.
During publication, the APT publisher will include any supported (and permitted) checksumtypes in any metadata files it publishes.

While the MD5 and SHA-1 algorithms are no longer considered secure, `pulp_deb` *requires* the presence of SHA-256 checksums to function, and is therefore *never* dependent on unsecure algorithms for integrity checking.
MD5 and SHA-1 are checked and used *in addition* to the other algorithms.
This is consistent with widespread usage within the larger Debian ecosystem.
