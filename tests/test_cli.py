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


if __name__ == "__main__": unittest.main()
