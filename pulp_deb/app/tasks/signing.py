import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.db.models import Q

from pulpcore.plugin.models import (
    Upload,
    UploadChunk,
    Artifact,
    ContentArtifact,
    CreatedResource,
    PulpTemporaryFile,
)
from pulpcore.plugin.tasking import add_and_remove, general_create
from pulpcore.plugin.util import get_url

from pulp_deb.app.models.signing_service import (
    AptPackageSigningService,
    DebPackageSigningResult,
    FingerprintMismatch,
    InvalidSignature,
    UnsignedPackage,
)
from pulp_deb.app.models import AptRepository, Package, PackageReleaseComponent

import logging
from gettext import gettext as _

log = logging.getLogger(__name__)


def _save_file(fileobj, final_package):
    with fileobj.file.open() as fd:
        final_package.write(fd.read())
    final_package.flush()


def _save_upload(uploadobj, final_package):
    chunks = UploadChunk.objects.filter(upload=uploadobj).order_by("offset")
    for chunk in chunks:
        final_package.write(chunk.file.read())
        chunk.file.close()
    final_package.flush()


def _create_signed_artifact(signed_package_path, result):
    if not signed_package_path.exists():
        raise Exception(f"Signing script did not create the signed package: {result}")
    artifact = Artifact.init_and_validate(str(signed_package_path))
    artifact.save()
    resource = CreatedResource(content_object=artifact)
    resource.save()
    return artifact


async def _sign_file(package_file, signing_service, signing_fingerprint):
    logging.info(
        _("Signing package %s with fingerprint %s"), package_file.name, signing_fingerprint
    )
    result = await signing_service.asign(package_file.name, pubkey_fingerprint=signing_fingerprint)
    signed_package_path = Path(result["deb_package"])
    return await asyncio.to_thread(_create_signed_artifact, signed_package_path, result)


def sign_and_create(
    app_label,
    serializer_name,
    signing_service_pk,
    signing_fingerprint,
    temporary_file_pk,
    *args,
    **kwargs,
):
    data = kwargs.pop("data", None)
    context = kwargs.pop("context", {})
    # Get unsigned package file and sign it
    package_signing_service = AptPackageSigningService.objects.get(pk=signing_service_pk)
    with NamedTemporaryFile(mode="wb", dir=".", delete=False) as final_package:
        try:
            uploaded_package = PulpTemporaryFile.objects.get(pk=temporary_file_pk)
            _save_file(uploaded_package, final_package)
        except PulpTemporaryFile.DoesNotExist:
            uploaded_package = Upload.objects.get(pk=temporary_file_pk)
            _save_upload(uploaded_package, final_package)

        artifact = asyncio.run(
            _sign_file(final_package, package_signing_service, signing_fingerprint)
        )
    uploaded_package.delete()
    # Create Package content
    data["artifact"] = get_url(artifact)
    # The Package serializer validation method have two branches: the signing and non-signing.
    # Here, the package is already signed, so we need to update the context for a proper validation.
    context["sign_package"] = False
    # The request data is immutable when there's an upload, so we can't delete the upload out of the
    # request data like we do for a file.  Instead, we'll delete it here.
    if "upload" in data:
        del data["upload"]
    general_create(app_label, serializer_name, data=data, context=context, *args, **kwargs)


def _sign_package(package, signing_service, signing_fingerprint, package_release_map):
    """
    Sign a package or reuse an existing signed result.

    Returns None if already signed with the fingerprint, otherwise a
    tuple of (original_package_id, new_package_id, prcs_to_update).
    """
    content_artifact = package.contentartifact_set.first()
    artifact_obj = content_artifact.artifact
    package_id = str(package.pk)

    with NamedTemporaryFile(mode="wb", dir=".", delete=False) as final_package:
        artifact_file = artifact_obj.file
        _save_file(artifact_file, final_package)

        # check if the package is already signed with our fingerprint
        try:
            signing_service.validate_signature(final_package.name)
            return None
        except (UnsignedPackage, InvalidSignature, FingerprintMismatch):
            pass

        # Collect PackageReleaseComponents that need to be updated
        prcs_to_update = list(
            PackageReleaseComponent.objects.filter(
                package_id=package_id, _pulp_domain=package._pulp_domain
            )
        )

        # check if the package has been signed in the past with our fingerprint
        if existing_result := DebPackageSigningResult.objects.filter(
            sha256=content_artifact.artifact.sha256,
            package_signing_fingerprint=signing_fingerprint,
        ).first():
            return (package_id, str(existing_result.result.pk), prcs_to_update)

        # create a new signed version of the package
        log.info(f"Signing package {package.name}.")
        artifact = asyncio.run(_sign_file(final_package, signing_service, signing_fingerprint))
        signed_package = package
        signed_package.pk = None
        signed_package.pulp_id = None
        signed_package.sha256 = artifact.sha256
        signed_package.save()
        ContentArtifact.objects.create(
            artifact=artifact,
            content=signed_package,
            relative_path=content_artifact.relative_path,
        )
        DebPackageSigningResult.objects.create(
            sha256=artifact_obj.sha256,
            package_signing_fingerprint=signing_fingerprint,
            result=signed_package,
        )

        resource = CreatedResource(content_object=signed_package)
        resource.save()
        log.info(f"Signed package {package.name}.")

        return (package_id, str(signed_package.pk), prcs_to_update)


def signed_add_and_remove(
    repository_pk, add_content_units, remove_content_units, base_version_pk=None
):
    repo = AptRepository.objects.get(pk=repository_pk)

    if repo.package_signing_service:
        # map packages to releases
        prcs = PackageReleaseComponent.objects.filter(
            Q(pk__in=add_content_units) | Q(pk__in=repo.content.all())
        ).select_related("package", "release_component")
        package_release_map = {prc.package_id: prc.release_component.distribution for prc in prcs}

        # Prepare package list with their fingerprints
        packages = []
        for package in Package.objects.filter(pk__in=add_content_units):
            # match the package's release to a fingerprint override if one exists
            fingerprint = repo.release_package_signing_fingerprint(
                package_release_map.get(package.pk)
            )
            packages.append((package, fingerprint))

        async def _sign_packages():
            semaphore = asyncio.Semaphore(settings.MAX_PACKAGE_SIGNING_WORKERS)

            async def _bounded_sign(pkg_tuple):
                pkg, fingerprint = pkg_tuple
                async with semaphore:
                    return await asyncio.to_thread(
                        _sign_package,
                        pkg,
                        repo.package_signing_service,
                        fingerprint,
                        package_release_map,
                    )

            return await asyncio.gather(*(_bounded_sign(pkg_tuple) for pkg_tuple in packages))

        for result in asyncio.run(_sign_packages()):
            if not result:
                continue
            old_id, new_id, prcs_to_update = result

            # Update the add_content_units list with the new package
            while old_id in add_content_units:
                add_content_units.remove(old_id)
            if new_id not in add_content_units:
                add_content_units.append(new_id)

            # Repoint PackageReleaseComponents that were collected during signing
            for prc in prcs_to_update:
                new_prc, _ = PackageReleaseComponent.objects.get_or_create(
                    release_component=prc.release_component,
                    package_id=new_id,
                    _pulp_domain=prc._pulp_domain,
                )

                while str(prc.pk) in add_content_units:
                    add_content_units.remove(str(prc.pk))

                if str(new_prc.pk) not in add_content_units:
                    add_content_units.append(str(new_prc.pk))

    return add_and_remove(repository_pk, add_content_units, remove_content_units, base_version_pk)
