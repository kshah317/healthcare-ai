"""
tests for generate_patients.py that don't need java or the synthea jar.

the real synthea run is slow and needs a 200 mb download, so these tests fake the parts
that touch the outside world and focus on the logic i actually wrote: sorting output
into folders, clearing old batches, and failing loudly when something is missing.

run with:  python -m unittest test_generate_patients.py
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import generate_patients as gp


def make_fake_synthea_output(root):
    """build a tiny folder that looks like what synthea writes to output/."""
    raw = Path(root) / "output"
    (raw / "csv").mkdir(parents=True)
    (raw / "fhir").mkdir(parents=True)
    (raw / "metadata").mkdir(parents=True)
    (raw / "csv" / "patients.csv").write_text("id,first\n1,alex\n")
    (raw / "csv" / "conditions.csv").write_text("patient,code\n1,123\n")
    (raw / "fhir" / "alex_smith.json").write_text("{}")
    (raw / "metadata" / "run.json").write_text("{}")
    return raw


class OrganizeOutputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.dest = self.root / "generated-patients"

    def tearDown(self):
        self.tmp.cleanup()

    def test_sorts_files_into_csv_and_fhir_folders(self):
        raw = make_fake_synthea_output(self.root)
        counts = gp.organize_output(raw, self.dest)

        self.assertEqual(counts, {"csv": 2, "fhir": 1})
        self.assertTrue((self.dest / "csv" / "patients.csv").exists())
        self.assertTrue((self.dest / "csv" / "conditions.csv").exists())
        self.assertTrue((self.dest / "fhir" / "alex_smith.json").exists())

    def test_ignores_folders_it_does_not_care_about(self):
        raw = make_fake_synthea_output(self.root)
        gp.organize_output(raw, self.dest)
        self.assertFalse((self.dest / "metadata").exists())

    def test_replaces_previous_batch(self):
        stale = self.dest / "csv" / "old_patients.csv"
        stale.parent.mkdir(parents=True)
        stale.write_text("old")

        raw = make_fake_synthea_output(self.root)
        gp.organize_output(raw, self.dest)
        self.assertFalse(stale.exists())

    def test_handles_missing_format_folder(self):
        raw = self.root / "output"
        (raw / "fhir").mkdir(parents=True)
        (raw / "fhir" / "only.json").write_text("{}")

        counts = gp.organize_output(raw, self.dest)
        self.assertEqual(counts, {"csv": 0, "fhir": 1})
        self.assertFalse((self.dest / "csv").exists())

    def test_raises_when_there_is_no_output(self):
        with self.assertRaises(FileNotFoundError):
            gp.organize_output(self.root / "nope", self.dest)


class EnsureJarTests(unittest.TestCase):
    def test_skips_download_when_jar_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = Path(tmp) / "synthea.jar"
            jar.write_text("pretend jar")
            with mock.patch("urllib.request.urlretrieve") as fake_download:
                self.assertEqual(gp.ensure_jar(jar, "http://example.invalid"), jar)
                fake_download.assert_not_called()

    def test_downloads_when_jar_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = Path(tmp) / "synthea.jar"
            with mock.patch("urllib.request.urlretrieve") as fake_download:
                gp.ensure_jar(jar, "http://example.invalid")
                fake_download.assert_called_once_with("http://example.invalid", jar)

    def test_failed_download_exits_with_a_clear_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = Path(tmp) / "synthea.jar"

            # simulate a download that writes a partial file and then dies
            def broken_download(url, path):
                Path(path).write_text("half a jar")
                raise OSError("network down")

            with mock.patch("urllib.request.urlretrieve", side_effect=broken_download):
                with self.assertRaises(SystemExit) as caught:
                    gp.ensure_jar(jar, "http://example.invalid")
            self.assertIn("couldn't download synthea", str(caught.exception))
            self.assertFalse(jar.exists())


class CheckJavaTests(unittest.TestCase):
    def test_exits_when_java_is_missing(self):
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaises(SystemExit) as caught:
                gp.check_java()
        self.assertIn("java isn't installed", str(caught.exception))

    def test_passes_when_java_is_present(self):
        with mock.patch("shutil.which", return_value="/usr/bin/java"):
            gp.check_java()


class RunSyntheaTests(unittest.TestCase):
    def test_builds_the_right_command(self):
        with mock.patch("subprocess.run") as fake_run:
            fake_run.return_value.returncode = 0
            gp.run_synthea(25, "/tmp/work", Path("synthea.jar"))

        command = fake_run.call_args.args[0]
        self.assertEqual(command[:3], ["java", "-jar", "synthea.jar"])
        self.assertIn("-p", command)
        self.assertEqual(command[command.index("-p") + 1], "25")
        self.assertIn("--exporter.csv.export=true", command)
        self.assertEqual(fake_run.call_args.kwargs["cwd"], "/tmp/work")

    def test_exits_when_synthea_fails(self):
        with mock.patch("subprocess.run") as fake_run:
            fake_run.return_value.returncode = 1
            with self.assertRaises(SystemExit):
                gp.run_synthea(5, "/tmp/work", Path("synthea.jar"))


# lets the tests run directly with python test_generate_patients.py
if __name__ == "__main__":
    unittest.main()
