import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class PackagingTests(unittest.TestCase):
    def test_pyinstaller_spec_builds_single_file_executable(self):
        spec = read("packaging/PDFTranslator.spec")

        self.assertIn("exclude_binaries=False", spec)
        self.assertNotIn("COLLECT(", spec)

    def test_install_script_passes_paths_to_powershell_through_environment(self):
        script = read("packaging/install.cmd")

        self.assertIn("$env:PDF_TRANSLATOR_INSTALL_DIR", script)
        self.assertIn("$env:PDF_TRANSLATOR_PAYLOAD", script)
        self.assertNotIn("'%INSTALL_DIR%", script)
        self.assertNotIn("'%START_MENU%", script)


if __name__ == "__main__":
    unittest.main()
