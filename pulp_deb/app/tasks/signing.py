from pathlib import Path
from tempfile import NamedTemporaryFile

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


def _sign_file(package_file, signing_service, signing_fingerprint):
    result = signing_service.sign(package_file.name, pubkey_fingerprint=signing_fingerprint)
    signed_package_path = Path(result["deb_package"])
    if not signed_package_path.exists():
        raise Exception(f"Signing script did not create the signed package: {result}")
    artifact = Artifact.init_and_validate(str(signed_package_path))
    artifact.save()
    resource = CreatedResource(content_object=artifact)
    resource.save()
    return artifact


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
    # The request data is immutable when there's an upload, so we can't delete the upload out of the
    # request data like we do for a file.  Instead, we'll delete it here.
    if "upload" in data:
        del data["upload"]
    general_create(app_label, serializer_name, data=data, context=context, *args, **kwargs)


def _update_content_units(content_units, old_pk, new_pk):
    while str(old_pk) in content_units:
        content_units.remove(str(old_pk))

    if str(new_pk) not in content_units:
        content_units.append(str(new_pk))

    # Repoint PackageReleaseComponents included in this transaction to the new package.
    for prc in PackageReleaseComponent.objects.filter(pk__in=content_units, package_id=old_pk):
        new_prc, _ = PackageReleaseComponent.objects.get_or_create(
            release_component=prc.release_component,
            package_id=new_pk,
            _pulp_domain=prc._pulp_domain,
        )

        while str(prc.pk) in content_units:
            content_units.remove(str(prc.pk))

        if str(new_prc.pk) not in content_units:
            content_units.append(str(new_prc.pk))


def _check_package_signature(repository, package_path):
    try:
        repository.package_signing_service.validate_signature(package_path)
    except (UnsignedPackage, InvalidSignature, FingerprintMismatch):
        return False

    return True


def signed_add_and_remove(
    repository_pk, add_content_units, remove_content_units, base_version_pk=None
):
    repo = AptRepository.objects.get(pk=repository_pk)

    if repo.package_signing_service:
        # sign each package and replace it in the add_content_units list
        for package in Package.objects.filter(pk__in=add_content_units):
            content_artifact = package.contentartifact_set.first()
            artifact_obj = content_artifact.artifact
            package_id = package.pk

            with NamedTemporaryFile(mode="wb", dir=".", delete=False) as final_package:
                artifact_file = artifact_obj.file
                _save_file(artifact_file, final_package)

                # check if the package is already signed with our fingerprint
                if _check_package_signature(repo, final_package.name):
                    continue

                # check if the package has been signed in the past with our fingerprint
                if existing_result := DebPackageSigningResult.objects.filter(
                    sha256=content_artifact.artifact.sha256,
                    package_signing_fingerprint=repo.package_signing_fingerprint,
                ).first():
                    _update_content_units(add_content_units, package_id, existing_result.result.pk)
                    continue

                # create a new signed version of the package
                artifact = _sign_file(
                    final_package, repo.package_signing_service, repo.package_signing_fingerprint
                )
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
                    package_signing_fingerprint=repo.package_signing_fingerprint,
                    result=signed_package,
                )

                _update_content_units(add_content_units, package_id, signed_package.pk)
                resource = CreatedResource(content_object=signed_package)
                resource.save()

    return add_and_remove(repository_pk, add_content_units, remove_content_units, base_version_pk)
