# Signing Service Creation

To sign your APT release files on your `pulp_deb` publications, you will first need to create a signing service of type `AptReleaseSigningService`.

## Prerequisites

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

## Example Signing Script

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

## Creation Steps

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
