# Sign Debian Packages

Sign a Debian package using a registered APT package signing service.

Currently, only on-upload signing is supported.

## On Upload

!!! tip "New in 3.9.0 (Tech Preview)"

Sign a Debian package when uploading it to a repository.

### Prerequisites

- Have an `AptPackageSigningService` registered
  (see the [signing service guide](site:pulp_deb/docs/user/guides/signing_service/)).
- Have the V4 fingerprint of the key you want to use. The key must be accessible by the signing
  service you are using (the fingerprint is forwarded via `PULP_SIGNING_KEY_FINGERPRINT`).

### Instructions

1. Configure a repository to enable signing.
    - Both `package_signing_service` and `package_signing_fingerprint` must be set on the
      repository (or provided via the REST API fields with the same names).
    - With those fields set, every package upload to the repository will be signed by the service.
    - Optionally, set `package_signing_fingerprint_release_overrides` if you need different keys per
      dist.
2. Upload a package to this repository.

### Example

```bash
# Create or update a repository with signing enabled
http POST $API_ROOT/repositories/deb/apt \
  name="MyDebRepo" \
  package_signing_service=$SIGNING_SERVICE_HREF \
  package_signing_fingerprint=$SIGNING_FINGERPRINT

# Upload a package
pulp deb content upload \
  --repository ${REPOSITORY} \
  --file ${DEB_FILE}
```

### Known Limitations

**Traffic overhead**: The signing of a package should happen inside of a Pulp worker.
  [By design](site:pulpcore/docs/dev/learn/plugin-concepts/#tasks),
  Pulp needs to temporarily commit the file to the default backend storage in order to make the Uploaded File available to the tasking system.
  This implies in some extra traffic, compared to a scenario where a task could process the file directly.

**No sign tracking**: We do not track signing information of a package.
