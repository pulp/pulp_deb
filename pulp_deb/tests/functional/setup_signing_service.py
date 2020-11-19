#!/usr/bin/env python3

import os
import sys


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: {} <path_to_signing_script>".format(sys.argv[0]))
        sys.exit(1)

    script_path = os.path.realpath(sys.argv[1])
    if not os.path.exists(script_path):
        print("Usage: {} <path_to_signing_script>".format(sys.argv[0]))
        sys.exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulpcore.app.settings")

    import django

    django.setup()

    from pulp_deb.app.models import AptReleaseSigningService

    AptReleaseSigningService.objects.create(
        name="sign_deb_release",
        script=script_path,
    )
