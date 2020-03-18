#!/bin/bash

set -e

RELEASE_FILE="$(/usr/bin/readlink -f $1)"
OUTPUT_DIR="$(/usr/bin/mktemp -d)"
DETACHED_SIGNATURE_PATH="${OUTPUT_DIR}/Release.gpg"
INLINE_SIGNATURE_PATH="${OUTPUT_DIR}/InRelease"
PUBLIC_KEY_PATH="${OUTPUT_DIR}/public.key"

GPG_KEY_ID="Pulp QE"

# Export a public key
/usr/bin/gpg --armor --export "${GPG_KEY_ID}" > ${PUBLIC_KEY_PATH}

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
       \"public_key\": \"${PUBLIC_KEY_PATH}\", \
       \"signatures\": { \
         \"inline\": \"${INLINE_SIGNATURE_PATH}\", \
         \"detached\": \"${DETACHED_SIGNATURE_PATH}\" \
       } \
     }
