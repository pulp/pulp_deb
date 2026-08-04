import asyncio
import logging
import subprocess
from gettext import gettext as _
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.db.models import Q
from pysequoia.packet import PacketPile, Tag

from pulpcore.plugin.models import (
    Artifact,
    ContentArtifact,
    CreatedResource,
    PulpTemporaryFile,
    Upload,
    UploadChunk,
)
from pulpcore.plugin.tasking import add_and_remove, general_create
from pulpcore.plugin.util import get_url

from pulp_deb.app.constants import (
    PACKAGE_UPLOAD_DEFAULT_COMPONENT,
    PACKAGE_UPLOAD_DEFAULT_DISTRIBUTION,
)
from pulp_deb.app.models import (
    AptRepository,
    Package,
    PackageReleaseComponent,
    ReleaseArchitecture,
    ReleaseComponent,
    SourcePackage,
    SourcePackageReleaseComponent,
)
from pulp_deb.app.models.signing_service import (
    AptPackageSigningService,
    DebPackageSigningResult,
)

log = logging.getLogger(__name__)


def _prepare_package_removals(repo, remove_content_units, base_version_pk, distribution, component):
    """Expand the removal list to include the release component relationships of each package.

    Removing a (source) package also requires removing its PackageReleaseComponent /
    SourcePackageReleaseComponent links. When a distribution/component is given, the removal is
    scoped to that component: a package is only removed from the repository if the scope held its
    last relationship, so packages linked elsewhere or not linked at all are kept.
    """
    # "*" removes all content, so there is nothing to resolve here.
    if "*" in remove_content_units:
        return

    repository_version = (
        repo.versions.get(pk=base_version_pk) if base_version_pk else repo.latest_version()
    )
    # A distribution/component narrows the removal to a single release component.
    scoped = distribution is not None or component is not None
    if scoped:
        distribution = distribution or PACKAGE_UPLOAD_DEFAULT_DISTRIBUTION
        component = component or PACKAGE_UPLOAD_DEFAULT_COMPONENT

    for model, relationship_model, relationship_field in (
        (Package, PackageReleaseComponent, "package"),
        (SourcePackage, SourcePackageReleaseComponent, "source_package"),
    ):
        units = model.objects.filter(pk__in=remove_content_units)
        relationships = relationship_model.objects.filter(
            **{
                f"{relationship_field}__in": units,
                "pk__in": repository_version.content,
            }
        )
        if scoped:
            scoped_relationships = relationships.filter(
                release_component__distribution=distribution,
                release_component__component=component,
            )
            # Relationships named in the request are removed alongside the scoped ones.
            removed_relationship_ids = set(
                relationship_model.objects.filter(pk__in=remove_content_units).values_list(
                    "pk", flat=True
                )
            )
            removed_relationship_ids.update(scoped_relationships.values_list("pk", flat=True))
            still_linked = relationships.exclude(pk__in=removed_relationship_ids)
            orphaned_unit_ids = {
                str(pk)
                for pk in scoped_relationships.values_list(f"{relationship_field}_id", flat=True)
            } - {str(pk) for pk in still_linked.values_list(f"{relationship_field}_id", flat=True)}
            kept_unit_ids = {
                str(pk) for pk in units.values_list("pk", flat=True)
            } - orphaned_unit_ids
            remove_content_units[:] = [
                content_id for content_id in remove_content_units if content_id not in kept_unit_ids
            ]
            relationships = scoped_relationships
        remove_content_units.extend(str(pk) for pk in relationships.values_list("pk", flat=True))


def _prepare_package_additions(add_content_units, distribution, component):
    """Expand the addition list with the metadata needed to publish the packages in a component.

    For each (source) package being added under a distribution/component, ensure the matching
    ReleaseComponent, ReleaseArchitecture and *ReleaseComponent relationships exist and add them
    to the content being added.
    """
    packages = list(Package.objects.filter(pk__in=add_content_units))
    source_packages = list(SourcePackage.objects.filter(pk__in=add_content_units))
    if not (packages or source_packages) or (distribution is None and component is None):
        return

    distribution = distribution or PACKAGE_UPLOAD_DEFAULT_DISTRIBUTION
    component = component or PACKAGE_UPLOAD_DEFAULT_COMPONENT
    release_component, _ = ReleaseComponent.objects.get_or_create(
        distribution=distribution, component=component
    )
    add_content_units.append(str(release_component.pk))
    # Each binary package needs its architecture and a link to the release component.
    for package in packages:
        architecture, _ = ReleaseArchitecture.objects.get_or_create(
            distribution=distribution, architecture=package.architecture
        )
        package_component, _ = PackageReleaseComponent.objects.get_or_create(
            release_component=release_component, package=package
        )
        add_content_units.extend([str(architecture.pk), str(package_component.pk)])
    # Source packages only need a link to the release component.
    for source_package in source_packages:
        source_package_component, _ = SourcePackageReleaseComponent.objects.get_or_create(
            release_component=release_component, source_package=source_package
        )
        add_content_units.append(str(source_package_component.pk))


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


def _verify_package_fingerprint(path, signing_fingerprint):
    """Verify if the deb package at path is signed with signing_fingerprint.

    Extracts the key ID from the _gpgorigin member of the .deb archive
    and compares it against the provided signing_fingerprint.
    """
    ar_proc = subprocess.run(
        ["ar", "p", path, "_gpgorigin"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if ar_proc.returncode != 0 or not ar_proc.stdout:
        log.info(f"No _gpgorigin found in {path} (unsigned package).")
        return False

    raw_fingerprint = signing_fingerprint.split(":", 1)[1].upper()

    for packet in PacketPile.from_bytes(ar_proc.stdout):
        if packet.tag != Tag.Signature:
            continue
        # Prefer the full issuer fingerprint (v6 keys may omit the short key ID)
        if packet.issuer_fingerprint is not None:
            if raw_fingerprint.upper() == packet.issuer_fingerprint.upper():
                return True
        if packet.issuer_key_id is not None:
            if raw_fingerprint.endswith(packet.issuer_key_id.upper()):
                return True

    log.debug(f"Fingerprint mismatch for {path}: expected {raw_fingerprint}.")
    return False


def _sign_file(package_file, signing_service, signing_fingerprint):
    """Sign a package and return the signed artifact."""
    prefix, raw_fingerprint = signing_fingerprint.split(":", 1)
    log.info(_("Signing package %s with fingerprint %s"), package_file.name, signing_fingerprint)
    result = signing_service.sign(
        package_file.name,
        env_vars={"PULP_SIGNING_FINGERPRINT_TYPE": prefix},
        pubkey_fingerprint=raw_fingerprint,
    )
    signed_package_path = Path(result["deb_package"])
    return _create_signed_artifact(signed_package_path, result)


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

        artifact = _sign_file(final_package, package_signing_service, signing_fingerprint)
    uploaded_package.delete()
    # Create Package content
    data["artifact"] = get_url(artifact)
    # The Package serializer validation method have two branches: the signing and non-signing.
    # Here, the package is already signed, so we need to update the context for a proper validation.
    context["sign_package"] = False
    context["signing_key"] = signing_fingerprint
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

        # check if the package is already signed with the repo's fingerprint
        if _verify_package_fingerprint(final_package.name, signing_fingerprint):
            log.info(f"Package {package.name} is already signed with {signing_fingerprint}.")
            return None

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
            log.info(f"Reusing previously signed package for {package.name}.")
            return (package_id, str(existing_result.result.pk), prcs_to_update)

        # create a new signed version of the package
        log.info(f"Signing package {package.name}.")
        artifact = _sign_file(final_package, signing_service, signing_fingerprint)
        signed_package = package
        signed_package.pk = None
        signed_package.pulp_id = None
        signed_package.sha256 = artifact.sha256
        # Only _gpgorigin signatures are supported currently, so packages have one signing key.
        signed_package.signing_keys = [signing_fingerprint]
        signed_package.save()
        ContentArtifact.objects.create(
            artifact=artifact,
            content=signed_package,
            relative_path=content_artifact.relative_path,
        )
        # get_or_create guards against concurrent signing of the same package, which
        # would otherwise violate the unique constraint and fail the task.
        signing_result, created = DebPackageSigningResult.objects.get_or_create(
            sha256=artifact_obj.sha256,
            package_signing_fingerprint=signing_fingerprint,
            defaults={"result": signed_package},
        )
        if not created:
            # Another worker won the race; reuse its result and let orphan cleanup
            # reap the redundant package we just created.
            log.info(f"Package {package.name} was signed concurrently; reusing existing result.")
            return (package_id, str(signing_result.result.pk), prcs_to_update)

        resource = CreatedResource(content_object=signed_package)
        resource.save()
        log.info(f"Signed package {package.name}.")

        return (package_id, str(signed_package.pk), prcs_to_update)


def signed_add_and_remove(
    repository_pk,
    add_content_units,
    remove_content_units,
    base_version_pk=None,
    overwrite=True,
    distribution=None,
    component=None,
):
    repo = AptRepository.objects.get(pk=repository_pk)

    _prepare_package_removals(repo, remove_content_units, base_version_pk, distribution, component)
    _prepare_package_additions(add_content_units, distribution, component)

    if repo.package_signing_service:
        log.info(
            f"Signing packages for repository {repo.name} with {repo.package_signing_service}."
        )
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

    return add_and_remove(
        repository_pk,
        add_content_units,
        remove_content_units,
        base_version_pk,
        overwrite=overwrite,
    )
