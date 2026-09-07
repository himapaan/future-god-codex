"""Tests for tools/check_repo.py.

The repository as committed must pass. Each other test copies the repository to a
temporary directory, plants one specific defect, and asserts that the matching
check catches it. Defect strings that the validator itself scans for are built
from fragments so that this test file does not trip the validator.
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import check_repo  # noqa: E402


def run(root):
    """Run the whole validator over ``root`` and return (exit code, output)."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = check_repo.main([root])
    return code, buffer.getvalue()


class CleanRepositoryTests(unittest.TestCase):
    def test_committed_repository_passes(self):
        code, output = run(REPO_ROOT)
        self.assertEqual(code, 0, output)
        self.assertNotIn("FAIL", output)

    def test_every_check_actually_ran(self):
        _, output = run(REPO_ROOT)
        for name, _ in check_repo.CHECKS:
            self.assertIn(name, output)


class PlantedFailureTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="codex-check-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.copy = os.path.join(self.root, "repo")
        shutil.copytree(
            REPO_ROOT, self.copy, ignore=shutil.ignore_patterns(".git", "__pycache__")
        )

    def path(self, rel):
        return os.path.join(self.copy, rel)

    def read(self, rel):
        with open(self.path(rel), encoding="utf-8") as handle:
            return handle.read()

    def write(self, rel, text):
        os.makedirs(os.path.dirname(self.path(rel)), exist_ok=True)
        with open(self.path(rel), "w", encoding="utf-8") as handle:
            handle.write(text)

    def append(self, rel, text):
        with open(self.path(rel), "a", encoding="utf-8") as handle:
            handle.write(text)

    def assertCaught(self, check_name):
        code, output = run(self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn("FAIL  %s" % check_name, output)

    # -- structure ---------------------------------------------------------

    def test_missing_required_file_is_caught(self):
        os.remove(self.path("NOTICE.md"))
        self.assertCaught("required files")

    def test_malformed_json_is_caught(self):
        self.write("codex.json", "{ not json")
        code, output = run(self.copy)
        self.assertEqual(code, 2, output)

    # -- content fidelity --------------------------------------------------

    def test_markdown_drift_from_json_is_caught(self):
        text = self.read("quotes/QUOTES.md").replace(
            "It is that they will learn to be us.",
            "It is that they will learn to be like us.",
        )
        self.write("quotes/QUOTES.md", text)
        self.assertCaught("JSON to Markdown agreement")

    def test_unverified_book_text_in_a_codex_page_is_caught(self):
        self.append(
            "codex/00-thesis.md",
            "\n> A sentence the book does not contain, presented as its own.\n",
        )
        self.assertCaught("quoted book text is verified")

    def test_unverified_book_text_with_an_attribution_is_caught(self):
        self.append(
            "README.md",
            "\n> Invented wording attributed to the author.\n\n"
            "*Future God*, Chapter 1, printed p. 3\n",
        )
        self.assertCaught("quoted book text is verified")

    def test_word_count_drift_is_caught(self):
        text = self.read("quotes/quotes.json").replace('"word_count": 25', '"word_count": 24', 1)
        self.write("quotes/quotes.json", text)
        self.assertCaught("excerpts and budget")

    def test_stale_verification_record_is_caught(self):
        text = self.read("quotes/quotes.json").replace(
            '"context": "Introduces', '"context": "Now introduces', 1
        )
        self.write("quotes/quotes.json", text)
        self.assertCaught("verification record is current")

    def test_glossary_growth_beyond_the_mvp_is_caught(self):
        text = self.read("glossary/glossary.json").replace('"term_count": 7', '"term_count": 8', 1)
        self.write("glossary/glossary.json", text)
        self.assertCaught("glossary")

    # -- boundaries --------------------------------------------------------

    def test_removing_the_disclosure_is_caught(self):
        text = self.read("README.md").replace("Future God prose and original ideas", "Someone wrote")
        self.write("README.md", text)
        self.assertCaught("AI disclosure")

    def test_duplicating_the_disclosure_is_caught(self):
        self.append("README.md", "\n" + check_repo.EXACT_DISCLOSURE + "\n")
        self.assertCaught("AI disclosure")

    def test_protocol_presented_as_available_is_caught(self):
        self.append("codex/02-anti-turing.md", "\nRun the Stillness Protocol daily.\n")
        self.assertCaught("Stillness Protocol boundary")

    def test_protocol_marked_present_in_json_is_caught(self):
        text = self.read("codex.json").replace('"present": false', '"present": true', 1)
        self.write("codex.json", text)
        self.assertCaught("Stillness Protocol boundary")

    def test_protocol_implementation_file_is_caught(self):
        self.write("tools/stillness_protocol.py", "VALUE = 1\n")
        self.assertCaught("Stillness Protocol boundary")

    def test_broken_relative_link_is_caught(self):
        self.append("README.md", "\nSee [the missing page](codex/99-nowhere.md).\n")
        self.assertCaught("relative links resolve")

    def test_missing_notice_link_is_caught(self):
        text = self.read("codex/03-practices.md").replace("NOTICE.md", "LICENSE")
        self.write("codex/03-practices.md", text)
        self.assertCaught("licensing statements")

    def test_truncated_license_is_caught(self):
        self.write("LICENSE", "Attribution-ShareAlike 4.0 International\n")
        self.assertCaught("licensing statements")

    # -- safety ------------------------------------------------------------

    def test_planted_token_is_caught(self):
        self.write("codex/leak.md", "token: " + "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5\n")
        self.assertCaught("no secrets, paths or trackers")

    def test_planted_local_path_is_caught(self):
        self.write("codex/leak.md", "see /" + "home/" + "someone/notes/draft.md\n")
        self.assertCaught("no secrets, paths or trackers")

    def test_planted_email_is_caught(self):
        self.write("codex/leak.md", "write to reader" + "@" + "example.com\n")
        self.assertCaught("no secrets, paths or trackers")

    def test_planted_tracking_identifier_is_caught(self):
        self.write("codex/leak.md", "container " + "GTM-" + "ABC1234\n")
        self.assertCaught("no secrets, paths or trackers")

    def test_planted_unpublished_title_is_caught(self):
        self.write("codex/leak.md", "the sequel, " + "Proto" + "luminal, arrives later\n")
        self.assertCaught("no secrets, paths or trackers")

    def test_planted_book_file_is_caught(self):
        self.write("quotes/future-god.pdf", "not really a pdf\n")
        self.assertCaught("no book files or binaries")

    def test_oversized_file_is_caught(self):
        self.write("codex/extract.md", "word " * 60000)
        self.assertCaught("no book files or binaries")

    def test_network_import_in_a_tool_is_caught(self):
        self.append("tools/verify_quotes.py", "\nimport " + "urllib.request\n")
        self.assertCaught("no network or process code")

    def test_shell_escape_in_a_tool_is_caught(self):
        self.append("tools/verify_quotes.py", "\nos." + "system('echo hi')\n")
        self.assertCaught("no network or process code")


if __name__ == "__main__":
    unittest.main()
