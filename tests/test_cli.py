import tempfile
import unittest
from pathlib import Path
from openhdo_cli.__main__ import scaffold, main
from openhdo_plugin import pack, unpack


class CliTests(unittest.TestCase):
    def test_python_scaffold_pack_validate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = scaffold(root / "plugin", "example.plugin", "python")
            package = pack(source, root / "plugin.hdop")
            self.assertEqual(unpack(package, root / "out")["entrypoints"]["python"], "backend/plugin.py")
            main(["validate", str(package)])

    def test_invalid_id_does_not_create_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "new"
            with self.assertRaises(ValueError): scaffold(target, "../bad", "python")
            self.assertFalse(target.exists())

    def test_scaffold_does_not_overwrite_project(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError): scaffold(directory, "example.plugin", "python")

    def test_scaffold_includes_versioned_release_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            source = scaffold(Path(directory) / "plugin", "example.plugin", "python")
            workflow = (source / ".github/workflows/plugin.yml").read_text("utf-8")
            self.assertIn("plugin-release.yml@v1.1.0", workflow)
            self.assertIn('tags: ["v*"]', workflow)
            self.assertIn("One HDO plugin = one repository", (source / "README.md").read_text("utf-8"))

    def test_release_tag_must_match_manifest_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = scaffold(root / "plugin", "example.plugin", "python")
            target = root / "plugin.hdop"
            with self.assertRaises(SystemExit):
                main(["pack", str(source), "--out", str(target), "--tag", "v2.0.0"])
            self.assertFalse(target.exists())
            main(["pack", str(source), "--out", str(target), "--tag", "v1.0.0"])
            self.assertTrue(target.is_file())

    def test_nested_plugin_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = scaffold(root / "plugin", "example.plugin", "python")
            nested = source / "another-plugin"
            nested.mkdir()
            (nested / "hdo.json").write_text("{}")
            with self.assertRaises(ValueError): pack(source, root / "plugin.hdop")


if __name__ == "__main__": unittest.main()
