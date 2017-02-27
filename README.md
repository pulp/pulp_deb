Debian Support
==============

Pulp plugin to handle Debian packages.

**WARNING:** There may be bugs.

### Requirements

Admin extensions do not need any additional tools.

Server extensions need:
* python-debian: https://pypi.python.org/pypi/python-debian
* python-debpkgr: https://pypi.python.org/pypi/python-debpkgr


### Installation

Build the RPMs from spec file.
Additionally, build python-debian and python-debpkgr as rpm packages.


### Signing support

To enable repository metadata signing, you will need to supply a configuration
file `/etc/pulp/server/plugins.conf.d/deb_distributor.json`, containing
something like:

```json
{
  "gpg_cmd": "/usr/local/bin/sign.sh",
  "gpg_key_id": "0452AB3D"
}

```

The supplied sign command has to be an executable accessible to the Apache
user. It will be supplied the path to a `Release` file to be signed, and is
expected to produce a file named `Release.gpg` in the same directory as the
`Release` file. Additionally, the sign command will be passed the following
environment variables:
* `GPG_CMD`
* `GPG_KEY_ID` (if specified in the configuration file)
* `GPG_REPOSITORY_NAME`
* `GPG_DIST`

The sign command may decide on a key ID to use, based on the repository name
or the dist that is being signed.

A minimal sign command using GPG could be:

```Shell
#!/bin/bash -e

KEYID=${GPG_KEY_ID:-45BA0816}

gpg --homedir /var/lib/pulp/gpg-home \
    --detach-sign --default-key $KEYID \
    --armor --output ${1}.gpg ${1}
```

You could import your password-less GPG keys like this:

```Shell
mkdir /var/lib/pulp/gpg-home
chmod 0700 /var/lib/pulp/gpg-home
gpg --homedir /var/lib/pulp/gpg-home --import <path-to-secret-keys>
chown -R apache.apache /var/lib/pulp/gpg-home
```

**WARNING!** The example, as presented above, is not suitable for production
use. Unprotected GPG keys may be easily stolen. You may want to consider
more secure alternatives for your signing needs, like a dedicated server,
potentially with a
[Hardware Security Module](https://en.wikipedia.org/wiki/Hardware_security_module).
