#!/usr/bin/env python3

import os
import sys


if __name__ == "__main__":

    usage_string = "Usage: {} <path_to_signing_script> <path_to_public_key_file>".format(
        sys.argv[0]
    )

    if len(sys.argv) != 3:
        print("ERROR: Not enough arguments!")
        print(usage_string)
        sys.exit(1)

    script_path = os.path.realpath(sys.argv[1])
    public_key_file = os.path.realpath(sys.argv[2])

    if not os.path.exists(script_path):
        print("ERROR: The signing script provided does not exist!")
        print(usage_string)
        sys.exit(1)

    if not os.path.exists(public_key_file):
        print("ERROR: The public key file provided does not exist!")
        print(usage_string)
        sys.exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulpcore.app.settings")

    import django

    django.setup()

    from pulp_deb.app.models import AptReleaseSigningService

    with open(public_key_file, "rb") as key:
        public_key = key.read()

    AptReleaseSigningService.objects.create(
        name="sign_deb_release",
        script=script_path,
        public_key=public_key,
        pubkey_fingerprint="6EDF301256480B9B801EBA3D05A5E6DA269D9D98",
    )
