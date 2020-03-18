import os
import gnupg
import tempfile
import subprocess
import json

from logging import getLogger
from json import JSONDecodeError

from pulpcore.plugin.models import SigningService

logger = getLogger(__name__)


class AptReleaseSigningService(SigningService):
    """
    A model used for signing Apt repository Release files.

    Will produce at least one of InRelease/Release.gpg
    """

    def validate(self):
        """
        Validate a signing service for a Apt repository Release file.

        The validation will ensure that the sign() function of the signing service will return a
        dict with the following structure:

        {
          "signatures": {
            "inline": "<relative_path>/InRelease",
            "detached": "<relative_path>/Release.gpg",
          }
          "public_key" : "<relative_path>/public.key"
        }

        It will also ensure that the so returned files do indeed provide valid signatures as
        expected.

        Raises:
            RuntimeError: The signing service failed to validate for the reason provided.
        """
        with tempfile.TemporaryDirectory() as temp_directory_name:
            test_release_path = os.path.join(temp_directory_name, "Release")
            with open(test_release_path, "wb") as test_file:
                test_data = b"arbitrary data"
                test_file.write(test_data)
                test_file.flush()
                return_value = self.sign(test_release_path)

                public_key_path = return_value.get("public_key")
                signatures = return_value.get("signatures")

                if not public_key_path:
                    message = "The signing service script must report a 'public_key' field!"
                    raise RuntimeError(message)

                if not signatures:
                    message = "The signing service script must report a 'signatures' field!"
                    raise RuntimeError(message)

                if not isinstance(signatures, dict):
                    message = (
                        "The 'signatures' field reported by the signing service script must "
                        "contain a dict!"
                    )
                    raise RuntimeError(message)

                if "inline" not in signatures and "detached" not in signatures:
                    message = (
                        "The dict contained in the 'signatures' field of the singing service "
                        "script must include an 'inline' field, a 'detached' field, or both!"
                    )
                    raise RuntimeError(message)

                for signature_type, signature_file in signatures.items():
                    if not os.path.exists(signature_file):
                        message = (
                            "The '{}' file, as reported in the 'signatures.{}' field of the "
                            "signing service script, doesn't appear to exist!"
                        )
                        raise RuntimeError(message.format(signature_file, signature_type))

                # Prepare GPG:
                gpg = gnupg.GPG(gnupghome=temp_directory_name)
                with open(public_key_path, "rb") as key:
                    gpg.import_keys(key.read())

                # Verify InRelease file
                inline_path = signatures.get("inline")
                if inline_path:
                    if os.path.basename(inline_path) != "InRelease":
                        message = (
                            "The path returned via the 'signatures.inline' field of the signing "
                            "service script, must end with the 'InRelease' file name!"
                        )
                        raise RuntimeError(message)
                    with open(inline_path, "rb") as inline:
                        verified = gpg.verify_file(inline)
                        if not verified.valid:
                            message = "GPG Verification of the inline file '{}' failed!"
                            raise RuntimeError(message.format(inline_path))

                    # Also check that the non-signature part of the InRelease file is the same as
                    # the original Release file!
                    with open(inline_path, "rb") as inline:
                        inline_data = inline.read()
                        if b"-----BEGIN PGP SIGNED MESSAGE-----\n" not in inline_data:
                            message = "PGP message header is missing in the inline file '{}'."
                            raise RuntimeError(message.format(inline_path))
                        if b"-----BEGIN PGP SIGNATURE-----\n" not in inline_data:
                            message = "PGP signature header is missing in inline file '{}'."
                            raise RuntimeError(message.format(inline_path))
                        if test_data not in inline_data:
                            message = (
                                "The inline file '{}' contains different data from the original "
                                "file."
                            )
                            raise RuntimeError(message.format(inline_path))

                # Verify Release.gpg file
                detached_path = signatures.get("detached")
                if detached_path:
                    if os.path.basename(detached_path) != "Release.gpg":
                        message = (
                            "The path returned via the 'signatures.detached' field of the signing "
                            "service script, must end with the 'Release.gpg' file name!"
                        )
                        raise RuntimeError(message)
                    with open(signatures.get("detached"), "rb") as detached:
                        verified = gpg.verify_file(detached, test_release_path)
                        if not verified.valid:
                            message = "GPG Verification of the detached file '{}' failed!"
                            raise RuntimeError(message.format(detached_path))

    def save(self, *args, **kwargs):
        """
        Save a signing service to the database (unless it fails to validate).
        """
        self.validate()
        super().save(*args, **kwargs)

    def sign(self, filename):
        """
        Create signature files for the passed filename, as expected for an APT release.

        Args:
            filename (str): A relative path to a file which is intended to be signed.

        Raises:
            RuntimeError: If a return code of the script is not equal to 0, indicating a failure.

        Returns:
            A dictionary as validated by the save() function above.
        """
        completed_process = subprocess.run(
            [self.script, filename], env={}, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if completed_process.returncode != 0:
            raise RuntimeError(str(completed_process.stderr))

        try:
            return_value = json.loads(completed_process.stdout)
        except JSONDecodeError:
            message = "The signing service script did not return valid JSON!"
            raise RuntimeError(message)

        return return_value
