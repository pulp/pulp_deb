#!/bin/bash

set -e

FILE_PATH="$(/usr/bin/readlink -f $1)"
FILE_DIR="$(/usr/bin/dirname "${FILE_PATH}")"
SIGNATURE_PATH="${FILE_DIR}/Release.gpg"
INLINE_SIGNATURE_PATH="${FILE_DIR}/InRelease"
PUBLIC_KEY_PATH="${FILE_DIR}/public.key"

GPG_KEY_ID="Pulp QE"

# Export a public key
/usr/bin/gpg --armor --export "${GPG_KEY_ID}" > $PUBLIC_KEY_PATH

COMMON_GPG_OPTS="--batch --armor --digest-algo SHA256"

# Create a detached signature
/usr/bin/gpg ${COMMON_GPG_OPTS} \
  --detach-sign \
  --output "${SIGNATURE_PATH}" \
  --local-user "${GPG_KEY_ID}" \
  "${FILE_PATH}"

# Create an inline signature
/usr/bin/gpg ${COMMON_GPG_OPTS} \
  --clearsign \
  --output "${INLINE_SIGNATURE_PATH}" \
  --local-user "${GPG_KEY_ID}" \
  "${FILE_PATH}"

echo {\"file\": \"${FILE_PATH}\", \
      \"signature\": \"${SIGNATURE_PATH}\", \
      \"key\": \"${PUBLIC_KEY_PATH}\"}
