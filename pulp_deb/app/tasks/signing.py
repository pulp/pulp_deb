from pathlib import Path
from tempfile import NamedTemporaryFile

from pulpcore.plugin.models import Upload, UploadChunk, Artifact, CreatedResource, PulpTemporaryFile
from pulpcore.plugin.tasking import general_create
from pulpcore.plugin.util import get_url

from pulp_deb.app.models.signing_service import AptPackageSigningService


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

        result = package_signing_service.sign(
            final_package.name, pubkey_fingerprint=signing_fingerprint
        )
        signed_package_path = Path(result["deb_package"])
        if not signed_package_path.exists():
            raise Exception(f"Signing script did not create the signed package: {result}")
        artifact = Artifact.init_and_validate(str(signed_package_path))
        artifact.save()
        resource = CreatedResource(content_object=artifact)
        resource.save()
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
