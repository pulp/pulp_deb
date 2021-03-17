.. _checksums:

Configure Checksum Handling
================================================================================

.. include:: ../external_references.rst

``pulp_deb`` supports the following checksum algorithms: MD5, SHA-1, SHA-256, and SHA-512.
However, only algorithms that are present in the ``ALLOWED_CONTENT_CHECKSUMS`` setting will actually be used.

.. warning::
   Starting with pulpcore version 3.11, pulpcore will remove ``md5`` and ``sha1`` from the list of ``ALLOWED_CONTENT_CHECKSUMS`` by default.
   At that point, those checksums will no longer be available for use by the ``pulp_deb`` plugin, unless users explicitly opt back in.
   Without opt in, the ``pulp_deb`` plugin will be unable to include the relevant metadata fields (``MD5Sum``, and ``SHA1``) in any metadata files (such as release files and package indecies), published by the plugin's APT publisher.
   Since it is almost universal practice within the Debian ecosystem to publish MD5 in particular, there is no telling what might break without it.
   As a result, it is recommended most ``pulp_deb`` users opt in to at least MD5.
   If you are unable to enable MD5 for compliance reasons, or if you are feeling adventurous, you are welcome to put the claim that MD5 is merely "highly recommended" to the test.

   See the `release file format`_ description in the Debian Wiki for more information.


Background: What are the checksums used for?
--------------------------------------------------------------------------------

APT repository metadata files (release files and package indecies) will typically include several checksums for all files that they reference.
During synchronization, ``pulp_deb`` will check the downloaded files against the checksums provided (so long as the checksum type is one of the supported algorithms and is present in the ``ALLOWED_CONTENT_CHECKSUMS`` setting).
Together with a valid (and trusted) release file signature this will guarantee the integrity of the synchronized repository.

During publication, the APT publisher will include any supported (and permitted) checksumtypes in any metadata files it publishes.

.. warning::
   While the APT publisher will respect the ``ALLOWED_CONTENT_CHECKSUMS`` setting, the verbatim publisher will publish the upstream metadata files *verbatim* (the exact same metadata file that was synchronized).
   As a result, the verbatim publisher is totally independent of (and does not respect) the ``ALLOWED_CONTENT_CHECKSUMS`` setting.
   If your policy prohibits the presence of certain checksum types, either do not use the verbatim publisher, or only synchronize repositories that are already compliant with your policy.


Opting in to MD5 and/or SHA1
--------------------------------------------------------------------------------

.. note::
   Up to pulpcore version 3.11 all supported checksums were enabled by default.
   In addition all ``pulp_deb`` versions compatible with pulpcore up to 3.11 simply break if the user actively disables any of the checksum types supported by the plugin.

To opt in to MD5 and SHA1 checksum handling users simply need to manually configure the ``ALLOWED_CONTENT_CHECKSUMS`` setting in the Pulp configuration file (normally found at ``/etc/pulp/settings.py``).

See the `pulpcore configuration documentation`_ for more information on configuration files and look for the section on ``ALLOWED_CONTENT_CHECKSUMS`` in the `pulpcore settings documentation`_ for more information on this setting.

Once you have updated your configuration file you will likely need to halt your Pulp instance, and then run the following command to ensure your DB is made consistent with your ``ALLOWED_CONTENT_CHECKSUMS`` setting:

.. code-block:: none

   pulpcore-manager handle-artifact-checksums

.. note::
   Missing checksums will need to be recalculated for all your artifacts which can take some time.
   If you have a missmatch between your configured ``ALLOWED_CONTENT_CHECKSUMS`` setting and the checksums present in the DB, Pulp will simply refuse to start.


Security Implications
--------------------------------------------------------------------------------

While the MD5 and SHA-1 algorithms are no longer considered secure, ``pulp_deb`` *requires* the presence of SHA-256 checksums to function, and is therefore *never* dependent on unsecure algorithms for integrity checking.
MD5 and SHA-1 are checked and used *in addition* to the other algorithms, purely for backwards compatibility.
This is consistent with widespread usage within the larger Debian ecosystem.


Disabling forbidden checksum warnings
--------------------------------------------------------------------------------

If your Pulp instance is configured to disallow the MD5 checksum algorithm, ``pulp_deb`` will emit a warning message with every sync as well as every use of the APT publisher.
You can disable these warnings, by setting ``FORBIDDEN_CHECKSUM_WARNINGS = False`` in your Pulp configuration file.
