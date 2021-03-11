#!/bin/bash

set -e

RELEASE_FILE="$(/usr/bin/readlink -f $1)"
OUTPUT_DIR="$(/usr/bin/mktemp -d)"
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
