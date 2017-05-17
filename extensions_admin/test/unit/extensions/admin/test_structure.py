from ...testbase import PulpClientTests
from pulp_deb.extensions.admin import structure


class StructureTests(PulpClientTests):
    def test_ensure_rpm_root(self):
        # Test
        returned_root_section = structure.ensure_root(self.cli)

        # Verify
        self.assertTrue(returned_root_section is not None)
        self.assertEqual(returned_root_section.name, structure.SECTION_ROOT)
        root_section = self.cli.find_section(structure.SECTION_ROOT)
        self.assertTrue(root_section is not None)
        self.assertEqual(root_section.name, structure.SECTION_ROOT)

    def test_ensure_rpm_root_idempotency(self):
        # Test
        structure.ensure_root(self.cli)
        returned_root_section = structure.ensure_root(self.cli)

        # Verify
        self.assertTrue(returned_root_section is not None)
        self.assertEqual(returned_root_section.name, structure.SECTION_ROOT)
        puppet_root_section = self.cli.find_section(structure.SECTION_ROOT)
        self.assertTrue(puppet_root_section is not None)
        self.assertEqual(puppet_root_section.name, structure.SECTION_ROOT)

    def test_ensure_repo_structure_no_root(self):
        # Test
        repo_section = structure.ensure_repo_structure(self.cli)

        # Verify
        self.assertTrue(repo_section is not None)
        self.assertEqual(repo_section.name, structure.SECTION_REPO)
        puppet_root_section = self.cli.find_section(structure.SECTION_ROOT)
        self.assertTrue(puppet_root_section is not None)

    def test_ensure_repo_structure_idempotency(self):
        # Test
        structure.ensure_repo_structure(self.cli)
        repo_section = structure.ensure_repo_structure(self.cli)

        # Verify
        self.assertTrue(repo_section is not None)
        self.assertEqual(repo_section.name, structure.SECTION_REPO)


class SectionRetrievalTests(PulpClientTests):
    def setUp(self):
        super(SectionRetrievalTests, self).setUp()
        structure.ensure_repo_structure(self.cli)

    def test_repo_section(self):
        section = structure.repo_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_REPO)

    def test_repo_remove_section(self):
        section = structure.repo_remove_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_REMOVE)

    def test_repo_uploads_section(self):
        section = structure.repo_uploads_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_UPLOADS)

    def test_repo_sync_section(self):
        section = structure.repo_sync_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_SYNC)

    def test_repo_sync_schedules_section(self):
        section = structure.repo_sync_schedules_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_SYNC_SCHEDULES)

    def test_repo_publish_section(self):
        section = structure.repo_publish_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_PUBLISH)

    def test_repo_export_section(self):
        section = structure.repo_export_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_EXPORT)

    def test_repo_group_section(self):
        section = structure.repo_group_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_GROUP)

    def test_repo_group_export_section(self):
        section = structure.repo_group_export_section(self.cli)
        self.assertEqual(section.name, structure.SECTION_EXPORT)
