# Signing Service Creation

## Metadata

To sign your APT release files on your `pulp_deb` publications, you will first need to create a signing service of type `AptReleaseSigningService`.

### Prerequisites

Creating a singing service requires the following:

- A unique name for the signing service, use `pulp signing-service list --field=name` to see what has been taken already.
- The public key fingerprint of the GPG key that the signing service should use for signing. The public key itself must be available in the pulp user's GPG home directory.
- A path to a signing script or executable that must meet the following criteria:
  - Must be executable by the user pulp is running as.
  - Must be available on each pulp worker.
  - Any dependencies must also be available on each pulp worker.
  - Must accept the path to the file to be signed as a argument, e.g.: `/tmp/LJDSFHD/Release`.
  - Must do at least one of the following using the GPG key specified in the signing service:
    - Clearsign the file and write the output to e.g.: `/tmp/LJDSFHD/InRelease`.
    - Detached-sign the file and write the output to e.g.: `/tmp/LJDSFHD/Release.gpg`
  - Must return a JSON dict detailing the path to any signed files, e.g.:
    ```json
    {
        "signatures": {
             "inline": "/tmp/LJDSFHD/InRelease",
             "detached": "/tmp/LJDSFHD/Release.gpg",
        }
    }
    ```

### Example Signing Script

The following example signing service script is used as part of the `pulp_deb` test suite:

```bash
#!/bin/bash

set -e

RELEASE_FILE="$(/usr/bin/readlink -f $1)"
OUTPUT_DIR="${PULP_TEMP_WORKING_DIR}"
DETACHED_SIGNATURE_PATH="${OUTPUT_DIR}/Release.gpg"
INLINE_SIGNATURE_PATH="${OUTPUT_DIR}/InRelease"
GPG_KEY_ID="Pulp QE"
COMMON_GPG_OPTS="--batch --armor --digest-algo SHA256"

# Create a detached signature
/usr/bin/gpg ${COMMON_GPG_OPTS} \
  --detach-sign \
  --output "${DETACHED_SIGNATURE_PATH}" \
  --local-user "${GPG_KEY_ID}" \
  "${RELEASE_FILE}"

# Create an inline signature
/usr/bin/gpg ${COMMON_GPG_OPTS} \
  --clearsign \
  --output "${INLINE_SIGNATURE_PATH}" \
  --local-user "${GPG_KEY_ID}" \
  "${RELEASE_FILE}"

echo { \
       \"signatures\": { \
         \"inline\": \"${INLINE_SIGNATURE_PATH}\", \
         \"detached\": \"${DETACHED_SIGNATURE_PATH}\" \
       } \
     }
```

It assumes that both public and secret key for `GPG_KEY_ID="Pulp QE"` is present in the GPG home of the Pulp user and that the secret key is not protecteded by a password.

### Creation Steps

1. Add the public key to your pulp users GPG home, for example, if pulp workers are running as the `pulp` user:
   ```bash
   sudo -u pulp gpg --import <path/to/public.gpg>
   ```
2. Deploy the signing service script and any dependencies to all your pulp workers.
3. Create the signing service:
   ```bash
   sudo -u pulp pulpcore-manager add-signing-service --class deb:AptReleaseSigningService \
     PulpQE </path/to/script> 6EDF301256480B9B801EBA3D05A5E6DA269D9D98
   ```
   Consult `pulpcore-manager add-signing-service --help` for more information.
4. You can retrieve the `pulp_href` of the newly created signing service using:
   ```bash
   pulp signing-service show --name=PulpQE | jq -r .pulp_href
   ```
5. Start [using the signing service to sign metadata](https://staging-docs.pulpproject.org/pulp_deb/docs/user/guides/publish/#metadata-signing).


## Packages

!!! tip "New in 3.9.0 (Tech Preview)"

Package signing is available as a tech preview beginning with pulp_deb 3.9.0. Unlike metadata
signing, package signing modifies the `.deb` file directly, so it uses the
`deb:AptPackageSigningService` class.

### Prerequisites

- Install `debsigs` and ensure it can access the private key you want to use.
- Familiarize yourself with the general signing instructions in
	[pulpcore](site:pulpcore/docs/admin/guides/sign-metadata/).
- Make sure the public key fingerprint you provide matches the key available to `debsigs`. During
	package uploads the fingerprint is passed to the script via the
	`PULP_SIGNING_KEY_FINGERPRINT` environment variable.

### Instructions

1. Create a signing script capable of signing a Debian package with `debsigs`.
		- The script receives the package path as its first argument.
		- The script must use `PULP_SIGNING_KEY_FINGERPRINT` to select the signing key.
		- The script should return JSON describing the signed file:
			```json
			{"deb_package": "/absolute/path/to/signed.deb"}
			```
2. Register the script with `pulpcore-manager add-signing-service`.
		- Use `--class "deb:AptPackageSigningService"`.
		- The public key fingerprint passed here is only used to validate the script registration.
3. Retrieve the signing service `pulp_href` for later use (for example via
	 `pulp signing-service show --name <NAME>`).

### Example

The following script illustrates how to sign packages using `debsigs`. It copies the uploaded file
into a working directory (defaulting to `PULP_TEMP_WORKING_DIR` when present), signs it in place,
and emits the JSON payload expected by pulp_deb.

```bash title="package-signing-script.sh"
#!/usr/bin/env bash
set -euo pipefail

PACKAGE_PATH=$1
FINGERPRINT="${PULP_SIGNING_KEY_FINGERPRINT:?PULP_SIGNING_KEY_FINGERPRINT is required}"
WORKDIR="${PULP_TEMP_WORKING_DIR:-$(mktemp -d)}"
SIGNED_PATH="${WORKDIR}/$(basename "${PACKAGE_PATH}")"

cp "${PACKAGE_PATH}" "${SIGNED_PATH}"
debsigs --sign=origin --default-key "${FINGERPRINT}" "${SIGNED_PATH}"

echo {"deb_package": "${SIGNED_PATH}"}
```

```bash
pulpcore-manager add-signing-service \
	"SimpleDebSigningService" \
	${SCRIPT_ABS_FILENAME} \
	${KEYID} \
	--class "deb:AptPackageSigningService"

pulp signing-service show --name "SimpleDebSigningService"
```

