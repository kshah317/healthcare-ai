# test_check_no_real_data.py
#
# tests for the guardrail checker. each test builds a tiny throwaway file and checks that the
# checker flags it (or leaves it alone). nothing here needs git, java, or the synthea download.
# the "scary" strings are put together from pieces so this file doesn't trip the checker itself.

import tempfile
import unittest
from pathlib import Path

import check_no_real_data as guard


class CheckTextTests(unittest.TestCase):
    def test_flags_social_security_number(self):
        # three digits, two digits, four digits with dashes is the ssn shape
        text = "patient ssn is " + "123" + "-" + "45" + "-" + "6789"
        problems = guard.check_text("notes.txt", text)
        self.assertEqual(len(problems), 1)
        self.assertIn("social security number", problems[0])

    def test_flags_medical_record_number(self):
        problems = guard.check_text("notes.txt", "MRN: " + "1234567")
        self.assertIn("medical record number", problems[0])

    def test_flags_aws_key(self):
        problems = guard.check_text("config.py", "key = " + "AKIA" + "ABCDEFGHIJKLMNOP")
        self.assertTrue(any("aws access key" in p for p in problems))

    def test_flags_hardcoded_password(self):
        problems = guard.check_text("config.py", 'password = "hunter2hunter2"')
        self.assertIn("hardcoded secret", problems[0])

    def test_ignores_placeholder_password(self):
        # a placeholder value is documentation, not a leak
        problems = guard.check_text("config.py", 'password = "your-password-here"')
        self.assertEqual(problems, [])

    def test_reports_line_number(self):
        text = "fine line\nanother fine line\nMRN: " + "7654321"
        problems = guard.check_text("notes.txt", text)
        self.assertTrue(problems[0].startswith("notes.txt:3:"))

    def test_clean_text_passes(self):
        self.assertEqual(guard.check_text("readme.md", "just some normal words"), [])


class CheckPathTests(unittest.TestCase):
    def test_blocks_env_file(self):
        self.assertEqual(len(guard.check_path(".env")), 1)

    def test_blocks_synthea_jar(self):
        self.assertEqual(len(guard.check_path("synthea-with-dependencies.jar")), 1)

    def test_blocks_generated_patients_folder(self):
        self.assertEqual(len(guard.check_path("generated-patients/csv/patients.csv")), 1)

    def test_allows_normal_files(self):
        self.assertEqual(guard.check_path("generate_patients.py"), [])


class CheckFileTests(unittest.TestCase):
    def test_scans_a_real_file_on_disk(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / "data.txt"
            bad.write_text("MRN: " + "9999999", encoding="utf-8")
            self.assertEqual(len(guard.check_file(bad)), 1)

    def test_skips_binary_files(self):
        with tempfile.TemporaryDirectory() as folder:
            blob = Path(folder) / "image.bin"
            blob.write_bytes(b"\xff\xfe\x00\x00" * 10)
            self.assertEqual(guard.check_file(blob), [])

    def test_main_returns_nonzero_when_something_is_found(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / "data.txt"
            bad.write_text("MRN: " + "9999999", encoding="utf-8")
            self.assertEqual(guard.main([str(bad)]), 1)

    def test_main_returns_zero_when_clean(self):
        with tempfile.TemporaryDirectory() as folder:
            ok = Path(folder) / "notes.txt"
            ok.write_text("nothing to see here", encoding="utf-8")
            self.assertEqual(guard.main([str(ok)]), 0)


if __name__ == "__main__":
    unittest.main()
