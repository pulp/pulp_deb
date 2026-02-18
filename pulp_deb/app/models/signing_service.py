import os
import shutil
import subprocess
import tempfile
from importlib.resources import files
from pathlib import Path
from typing import Optional

import gnupg
from django.db import models
from pulpcore.plugin.models import BaseModel, Content, SigningService


class UnsignedPackage(Exception):
    """Raised when a deb package is unsigned and has no _gpgorigin signature."""


class InvalidSignature(Exception):
    """When GPG verification fails due to the signature (NO_PUBKEY, EXPSIG, etc)."""


class FingerprintMismatch(Exception):
    """Raised when a deb package is signed with a different key fingerprint."""


def prepare_gpg(temp_directory_name, public_key, pubkey_fingerprint):
    # Prepare GPG:
    # gpg = gnupg.GPG(gnupghome=temp_directory_name)
    gpg = gnupg.GPG(keyring=str(Path(temp_directory_name) / ".keyring"))
    gpg.import_keys(public_key)
    imported_keys = gpg.list_keys()

    if len(imported_keys) != 1:
        message = "We have imported more than one key! Aborting validation!"
        raise RuntimeError(message)

    if imported_keys[0]["fingerprint"] != pubkey_fingerprint:
        message = "The signing service fingerprint does not appear to match its public key!"
        raise RuntimeError(message)
    return gpg


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
        }

        It will also ensure that the so returned files do indeed provide valid signatures as
        expected.

        Raises:
            RuntimeError: The signing service failed to validate for the reason provided.
        """
        with tempfile.TemporaryDirectory() as temp_directory_name:
            test_release_path = os.path.join(temp_directory_name, "Release")
            temp_env = {"PULP_TEMP_WORKING_DIR": temp_directory_name}
            with open(test_release_path, "wb") as test_file:
                test_data = b"arbitrary data"
                test_file.write(test_data)
                test_file.flush()
                return_value = self.sign(test_release_path, env_vars=temp_env)

                signatures = return_value.get("signatures")

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
                gpg = prepare_gpg(temp_directory_name, self.public_key, self.pubkey_fingerprint)

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

                        if verified.pubkey_fingerprint != self.pubkey_fingerprint:
                            message = "'{}' appears to have been signed using the wrong key!"
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

                        if verified.pubkey_fingerprint != self.pubkey_fingerprint:
                            message = "'{}' appears to have been signed using the wrong key!"
                            raise RuntimeError(message.format(detached_path))


class AptPackageSigningService(SigningService):
    """
    A model used for signing Apt packages.

    The pubkey_fingerprint should be passed explicitly in the sign method.
    """

    def _env_variables(self, env_vars=None):
        # Prevent the signing service pubkey to be used for signing a package.
        # The pubkey should be provided explicitly.
        _env_vars = {"PULP_SIGNING_KEY_FINGERPRINT": None}
        if env_vars:
            _env_vars.update(env_vars)
        return super()._env_variables(_env_vars)

    def sign(
        self,
        filename: str,
        env_vars: Optional[dict] = None,
        pubkey_fingerprint: Optional[str] = None,
    ):
        """
        Sign a package @filename using @pubkey_fingerprint.

        Args:
            filename: The absolute path to the package to be signed.
            env_vars: (optional) Dict of env_vars to be passed to the signing script.
            pubkey_fingerprint: The V4 fingerprint that correlates with the private key to use.
        """
        if not pubkey_fingerprint:
            raise ValueError("A pubkey_fingerprint must be provided.")
        _env_vars = env_vars or {}
        _env_vars["PULP_SIGNING_KEY_FINGERPRINT"] = pubkey_fingerprint
        return super().sign(filename, _env_vars)

    async def asign(
        self,
        filename: str,
        env_vars: Optional[dict] = None,
        pubkey_fingerprint: Optional[str] = None,
    ):
        """
        Asynchronously sign a package @filename using @pubkey_fingerprint.

        Args:
            filename: The absolute path to the package to be signed.
            env_vars: (optional) Dict of env_vars to be passed to the signing script.
            pubkey_fingerprint: The V4 fingerprint that correlates with the private key to use.
        """
        if not pubkey_fingerprint:
            raise ValueError("A pubkey_fingerprint must be provided.")
        _env_vars = env_vars or {}
        _env_vars["PULP_SIGNING_KEY_FINGERPRINT"] = pubkey_fingerprint
        return await super().asign(filename, _env_vars)

    def validate(self):
        """
        Validate a signing service for an Apt package signature.

        Specifically, it validates that self.signing_script can sign an apt package with
        the sample key self.pubkey and that the self.sign() method returns:

        ```json
        {"apt_package": "<path/to/package.deb>"}
        ```

        Recreates the check that "debsig-verify" would be doing because debsig-verify is
        complicated to set up correctly, and doing so would add a dependency that is not available
        on rpm-based systems.
        """
        with tempfile.TemporaryDirectory() as temp_directory_name:
            # copy test deb package
            sample_deb = shutil.copy(
                files("pulp_deb").joinpath("tests/functional/data/packages/frigg_1.0_ppc64.deb"),
                temp_directory_name,
            )
            return_value = self.sign(sample_deb, pubkey_fingerprint=self.pubkey_fingerprint)
            try:
                signed_deb = return_value["deb_package"]
            except KeyError:
                raise Exception(f"Malformed output from signing script: {return_value}")

            self.validate_signature(signed_deb)

    def validate_signature(self, deb_package_path: str):
        """Validate that the deb package is signed with our pubkey."""
        with tempfile.TemporaryDirectory() as temp_directory_name:
            gpg = prepare_gpg(temp_directory_name, self.public_key, self.pubkey_fingerprint)

            self._check_deb_signature(
                deb_package_path, self.pubkey_fingerprint, temp_directory_name, gpg
            )

    @staticmethod
    def _check_deb_signature(
        deb_package_path: str, fingerprint: str, temp_directory_name: str, gpg: gnupg.GPG
    ):
        """Check the deb package signature matches the provided fingerprint."""
        # unpack the archive
        cmd = ["ar", "x", deb_package_path]
        res = subprocess.run(cmd, cwd=temp_directory_name, capture_output=True)
        if res.returncode != 0:
            raise Exception(f"Failed to read package {deb_package_path}. Please check the package.")

        # cat the unpacked archive bits together
        temp_dir = Path(temp_directory_name)
        with (temp_dir / "combined").open("wb") as combined:
            for filename in ("debian-binary", "control.*", "data.*"):
                # There will only be one control.tar.gz (or whatever) file, but we have to glob
                # and iterate because the compression type can vary.
                for x in temp_dir.glob(filename):
                    with x.open("rb") as f:
                        shutil.copyfileobj(f, combined)

        # verify combined data with _gpgorigin detached signature
        gpgorigin_path = temp_dir / "_gpgorigin"
        if not gpgorigin_path.exists():
            raise UnsignedPackage(
                f"_gpgorigin file not found for {deb_package_path}. Package is unsigned."
            )
        with gpgorigin_path.open("rb") as gpgorigin:
            verified = gpg.verify_file(gpgorigin, str(temp_dir / "combined"))
            if not verified.valid:
                raise InvalidSignature(
                    f"GPG Verification of the signed package {deb_package_path} failed!"
                )
            if verified.pubkey_fingerprint != fingerprint:
                raise FingerprintMismatch(
                    f"'{deb_package_path}' appears to have been signed using the wrong key!"
                )


class DebPackageSigningResult(BaseModel):
    """
    A model used for storing the result of signing a deb package.
    """

    sha256 = models.TextField(max_length=64)
    package_signing_fingerprint = models.TextField(max_length=40)
    result = models.ForeignKey(Content, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("sha256", "package_signing_fingerprint")
