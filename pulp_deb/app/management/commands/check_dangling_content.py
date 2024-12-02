from gettext import gettext as _
from django.core.management import BaseCommand
from pulpcore.plugin.models import RepositoryVersion

from pulp_deb.app.models.content.content import Package
from pulp_deb.app.models.content.structure_content import PackageReleaseComponent
from pulp_deb.app.models.repository import AptRepository


class Command(BaseCommand):
    """
    Check for dangling content in apt repository versions.
    """

    help = _(__doc__)

    def handle(self, *args, **options):
        """Implement the command."""
        repo_qs = AptRepository.objects.all()
        repo_version_qs = RepositoryVersion.objects.filter(repository__in=repo_qs)

        dangling_content = False
        dc_details = []

        for repo_version in repo_version_qs:
            content = repo_version.get_content()
            package_ids = set(
                Package.objects.filter(
                    pk__in=content.filter(pulp_type=Package.get_pulp_type())
                ).values_list("pulp_id", flat=True)
            )
            prc_qs = PackageReleaseComponent.objects.filter(
                pk__in=content.filter(
                    pulp_type=PackageReleaseComponent.get_pulp_type()
                ).values_list("pk", flat=True)
            )
            prc_ids = set(prc_qs.values_list("package__pulp_id", flat=True))

            if prc_ids != package_ids:
                dangling_content = True
                dc_package_ids = prc_ids - package_ids
                dc_prcs = prc_qs.filter(package__pulp_id__in=dc_package_ids)
                dc_details.append(
                    {
                        "repo_version": repo_version,
                        "dangling_prcs": list(dc_prcs),
                    }
                )

        if dangling_content:
            for detail in dc_details:
                dc_prcs_output = "\n".join(str(prc) for prc in detail["dangling_prcs"])
                self.stdout.write(
                    f"\n{'-' * 40}\n"
                    f"Dangling content found in {detail['repo_version']}:\n"
                    f"{'-' * 40}\n"
                    f"Dangling PRCs:\n{dc_prcs_output}"
                )
            self.stdout.write(f"{'-' * 40}\n")
            self.stdout.write(f"\nTotal affected repository versions: {len(dc_details)}\n")
            self.stdout.write(f"{'=' * 40}\n")
        else:
            self.stdout.write(f"{'=' * 40}\n")
            self.stdout.write("No dangling content found.\n")
            self.stdout.write(f"{'=' * 40}\n")
