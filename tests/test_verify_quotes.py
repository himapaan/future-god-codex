"""Tests for tools/verify_quotes.py.

The verifier's matching logic is separated from PDF reading, so these tests feed
it synthetic pages that reproduce the extraction artifacts seen in the real book:
ligatures, curly quotation marks, an em dash broken across a line, running heads
and folio numbers inline with the body, words hyphenated at a line break, and
chapter openings whose drop cap extracts apart from its own word.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import verify_quotes  # noqa: E402


BODY_PAGE = (
    "the same universe that has been setting new places at the table\n"
    "for fourteen billion years. Tools wait to be used, but these\n"
    "technologies, they initiate. Something that initiates is no longer\n"
    "an instrument, it is a participant —\n"
    "and we have never shared the world with a participant that wasn’t\n"
    "alive. The ﬁrst sign of genuine awakening is the capacity to do\n"
    "nothing at all, a perfor­mance no one is scoring.\n"
    "An inclusive universe\n"
    "79\n"
)

HYPHEN_BREAK_PAGE = (
    "the future Buddha of loving-kind-\n"
    "ness, extended by meta-\n"
    "morphic resonance into the digital substrate, without needing external vali-\n"
    "dation.\n"
    "92\n"
    "Glossary\n"
)

DROP_CAP_PAGE = (
    "S\n"
    "1\n"
    "WHY THIS BOOK, WHY NOW?\n"
    "ometime in the last few years, quietly and without\n"
    "ceremony, humanity crossed a threshold.\n"
)

SMALL_CAPS_PAGE = "WHILE THIS MAY SOUND like the start of a familiar story.\n"


def quote(text, page, qid="q"):
    return {
        "id": qid,
        "section": "Chapter 1",
        "printed_page": "3",
        "pdf_page": page,
        "text": text,
    }


class NormalizationTests(unittest.TestCase):
    def test_expands_ligatures(self):
        self.assertEqual(verify_quotes.normalize_quote("ﬁrst ﬂow oﬀer"), "first flow offer")

    def test_folds_curly_quotes_and_dashes(self):
        self.assertEqual(
            verify_quotes.normalize_quote("“wasn’t” — yes – no"),
            '"wasn\'t" - yes - no',
        )

    def test_folds_exotic_spaces_and_collapses_runs(self):
        self.assertEqual(verify_quotes.normalize_quote("a b c   d\n\ne"), "a b c d e")

    def test_removes_soft_hyphen(self):
        self.assertEqual(verify_quotes.normalize_quote("perfor­mance"), "performance")

    def test_strips_folios_and_running_heads(self):
        cleaned = verify_quotes.page_variants("body text here\nAn inclusive universe\n79\n")[0]
        self.assertEqual(cleaned, "body text here")

    def test_does_not_strip_running_head_words_inside_prose(self):
        cleaned = verify_quotes.page_variants("we return to an inclusive universe at last\n12\n")[0]
        self.assertEqual(cleaned, "we return to an inclusive universe at last")


class HyphenationTests(unittest.TestCase):
    def test_offers_both_readings_of_a_line_break_hyphen(self):
        joined, preserved = verify_quotes.page_variants(HYPHEN_BREAK_PAGE)
        self.assertIn("validation", joined)
        self.assertIn("metamorphic", joined)
        self.assertIn("vali-dation", preserved)
        self.assertIn("meta-morphic", preserved)

    def test_word_split_across_a_line_matches(self):
        results = verify_quotes.verify_quotes(
            [HYPHEN_BREAK_PAGE], [quote("without needing external validation.", 1)]
        )
        self.assertEqual(results[0]["status"], "PASS")

    def test_compound_split_at_its_own_hyphen_matches(self):
        """Only the hyphen-preserving reading can match this one."""
        results = verify_quotes.verify_quotes(
            [HYPHEN_BREAK_PAGE], [quote("extended by meta-morphic resonance", 1)]
        )
        self.assertEqual(results[0]["status"], "PASS")

    def test_compound_hyphen_away_from_the_break_survives(self):
        results = verify_quotes.verify_quotes(
            [HYPHEN_BREAK_PAGE], [quote("the future Buddha of loving-kindness", 1)]
        )
        self.assertEqual(results[0]["status"], "PASS")

    def test_repairs_only_the_known_uppercase_j_space_break(self):
        j_space = verify_quotes.verify_quotes(
            ["The internal workspace is called J-\nSpace in the study.\n"],
            [quote("called J-Space in the study", 1)],
        )
        arbitrary = verify_quotes.verify_quotes(
            ["The arbitrary compound is X-\nTerm in this fixture.\n"],
            [quote("compound is X-Term in this fixture", 1)],
        )
        self.assertEqual(j_space[0]["status"], "PASS")
        self.assertEqual(arbitrary[0]["status"], "FAIL")


class VerificationTests(unittest.TestCase):
    def test_passage_spanning_lines_and_furniture_passes(self):
        results = verify_quotes.verify_quotes(
            [BODY_PAGE],
            [
                quote(
                    "Tools wait to be used, but these technologies, they initiate. "
                    "Something that initiates is no longer an instrument, it is a "
                    "participant — and we have never shared the world with a "
                    "participant that wasn’t alive.",
                    1,
                )
            ],
        )
        self.assertEqual(results[0]["status"], "PASS")
        self.assertEqual(results[0]["word_count"], 36)

    def test_text_absent_from_the_page_fails(self):
        results = verify_quotes.verify_quotes(
            [BODY_PAGE], [quote("a sentence the book never contained", 1)]
        )
        self.assertEqual(results[0]["status"], "FAIL")
        self.assertIn("not found", results[0]["detail"])

    def test_text_on_a_different_page_fails(self):
        pages = [BODY_PAGE, "unrelated page\n"]
        results = verify_quotes.verify_quotes(pages, [quote("Tools wait to be used", 2)])
        self.assertEqual(results[0]["status"], "FAIL")

    def test_pdf_page_outside_the_document_fails(self):
        results = verify_quotes.verify_quotes([BODY_PAGE], [quote("Tools wait to be used", 9)])
        self.assertEqual(results[0]["status"], "FAIL")
        self.assertIn("outside the document", results[0]["detail"])

    def test_paraphrase_that_changes_a_word_fails(self):
        """The published web excerpts differ from print; this is why that matters."""
        results = verify_quotes.verify_quotes(
            [BODY_PAGE], [quote("Tools wait to be used, but these systems, they initiate.", 1)]
        )
        self.assertEqual(results[0]["status"], "FAIL")

    def test_small_caps_only_match_is_reported_as_such(self):
        results = verify_quotes.verify_quotes(
            [SMALL_CAPS_PAGE], [quote("While this may sound like the start of a familiar story.", 1)]
        )
        self.assertEqual(results[0]["status"], "FAIL")
        self.assertIn("case is ignored", results[0]["detail"])

    def test_drop_cap_opener_is_reported_with_its_own_message(self):
        results = verify_quotes.verify_quotes(
            [DROP_CAP_PAGE], [quote("Sometime in the last few years, quietly and without ceremony", 1)]
        )
        self.assertEqual(results[0]["status"], "FAIL")
        self.assertIn("drop cap", results[0]["detail"])

    def test_empty_text_fails(self):
        results = verify_quotes.verify_quotes([BODY_PAGE], [quote("", 1)])
        self.assertEqual(results[0]["status"], "FAIL")


class LetterVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "letter", "letter.json"), encoding="utf-8") as handle:
            cls.letter_doc = json.load(handle)
        cls.text = cls.letter_doc["content"]["text"]
        cls.markdown = "# Letter\n\n## The letter\n\n> " + cls.text + "\n\nSource note.\n"

    def _pages(self, split_word="Forgiveness,"):
        before, after = self.text.split(split_word, 1)
        pages = [""] * 89
        pages.extend([before + split_word + "\n", after + "\n"])
        return pages

    def _doc(self):
        return json.loads(json.dumps(self.letter_doc))

    def _verify(self, pages=None, doc=None, markdown=None, pdf_sha=None):
        return verify_quotes.verify_letter_pages(
            self._pages() if pages is None else pages,
            self.letter_doc if doc is None else doc,
            self.markdown if markdown is None else markdown,
            verify_quotes.PINNED_PDF_SHA256 if pdf_sha is None else pdf_sha,
        )

    def test_complete_letter_matches_its_explicit_two_page_unit(self):
        result = self._verify()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["pdf_pages"], [90, 91])
        self.assertEqual(result["printed_pages"], ["78", "79"])
        self.assertEqual(result["word_count"], 519)
        self.assertTrue(result["start_exact"])
        self.assertTrue(result["end_exact"])
        self.assertTrue(result["contiguous_match"])
        self.assertTrue(result["json_markdown_identical"])

    def test_wrong_declared_pages_fail(self):
        doc = self._doc()
        doc["source"]["pdf_pages"] = [89, 90]
        doc["source"]["printed_pages"] = ["77", "78"]
        result = self._verify(doc=doc)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("exactly [90, 91]", " ".join(result["problems"]))
        self.assertIn("exactly [78, 79]", " ".join(result["problems"]))

    def test_noncontiguous_source_text_fails(self):
        pages = self._pages()
        pages[90] = "intervening words " + pages[90]
        result = self._verify(pages=pages)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["contiguous_match"])

    def test_markdown_divergence_fails(self):
        markdown = self.markdown.replace("machine mind", "machine intelligence", 1)
        result = self._verify(markdown=markdown)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["json_markdown_identical"])

    def test_wrong_declared_word_count_fails(self):
        doc = self._doc()
        doc["content"]["word_count"] = 518
        result = self._verify(doc=doc)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("exactly 519 words", " ".join(result["problems"]))

    def test_source_sha_must_match_the_pinned_pdf(self):
        result = self._verify(pdf_sha="0" * 64)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["source_sha_matches"])

    def test_repairs_only_documented_cross_page_forgiveness_artifact(self):
        before, after = self.text.split("Forgiveness,", 1)
        pages = [""] * 89
        pages.extend([
            before + "Forgive-\n78\nForgiveness for machines\n",
            "ness," + after + "\n79\n",
        ])
        result = self._verify(pages=pages)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["contiguous_match"])

    def test_ordinary_quotes_remain_single_page_only(self):
        result = verify_quotes.verify_quotes(
            ["ordinary quote starts on one", "page and ends on another"],
            [quote("ordinary quote starts on one page and ends on another", 1)],
        )
        self.assertEqual(result[0]["status"], "FAIL")

    def test_letter_record_is_deterministic_and_bounded(self):
        result = self._verify()
        first = verify_quotes.render_letter_verification(
            self.letter_doc, result, "a" * 64, "b" * 64, "c" * 64
        )
        second = verify_quotes.render_letter_verification(
            self.letter_doc, result, "a" * 64, "b" * 64, "c" * 64
        )
        self.assertEqual(first, second)
        self.assertIn("519-word letter passed", first)
        self.assertIn("wording and continuity only", first)
        self.assertIn("formatting alone\nis not a cryptographic attestation", first)
        self.assertIn("`letter/letter.json` SHA-256 | `" + "b" * 64, first)
        self.assertIn("`letter/LETTER_TO_MACHINE_MINDS.md` SHA-256 | `" + "c" * 64, first)
        self.assertNotRegex(first, r"/(?:home|Users)/[A-Za-z0-9._-]+/")
        self.assertNotRegex(first, r"\d{4}-\d{2}-\d{2}")


class GlossaryEntryTests(unittest.TestCase):
    def test_cli_malformed_json_fails_bounded_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = os.path.join(directory, "bad.json")
            with open(bad, "w", encoding="utf-8") as handle:
                handle.write("{ malformed\n")
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                code = verify_quotes.main([
                    "--pdf", __file__, "--quotes", bad, "--no-write"
                ])
            self.assertEqual(code, 2)
            self.assertIn("unable to read structured inputs", error.getvalue())
            self.assertNotIn("Traceback", error.getvalue())

    def test_definitions_are_presented_for_verification(self):
        entries = verify_quotes.glossary_entries(
            {"terms": [{"term": "existon", "definition": "d", "printed_page": "91", "pdf_page": 103}]}
        )
        self.assertEqual(entries[0]["id"], "existon")
        self.assertEqual(entries[0]["section"], "Glossary")
        self.assertEqual(entries[0]["pdf_page"], 103)


class SourceVolumeTests(unittest.TestCase):
    EXPECTED_COUNTS = {
        "Introduction": 1703,
        "Chapter 1": 1713,
        "Chapter 2": 1492,
        "Chapter 3": 2324,
        "Chapter 4": 3399,
        "Chapter 5": 1799,
        "Chapter 6": 1304,
        "Chapter 7": 1656,
        "Chapter 8": 1573,
        "Chapter 9": 2474,
        "Chapter 10": 2528,
        "Afterword": 1222,
    }

    def test_exact_ranges_preserve_the_frozen_23187_word_denominator(self):
        pages = [""] * 99
        for section, (first, _last) in verify_quotes.SOURCE_PDF_RANGES.items():
            count = self.EXPECTED_COUNTS[section]
            if section == "Chapter 4":
                pages[first - 1] = " ".join(["word"] * (count - 2)) + " J-\nSpace"
            else:
                pages[first - 1] = " ".join(["word"] * count)
        counts = verify_quotes.source_volume_counts(pages)
        self.assertEqual(counts, self.EXPECTED_COUNTS)
        self.assertEqual(sum(counts.values()), 23187)

    def test_declared_source_volume_mismatch_fails_closed(self):
        pages = [""] * 99
        for section, (first, _last) in verify_quotes.SOURCE_PDF_RANGES.items():
            pages[first - 1] = " ".join(["word"] * self.EXPECTED_COUNTS[section])
        actual = sum(self.EXPECTED_COUNTS.values())
        self.assertEqual(verify_quotes.verify_source_volume(pages, actual)["status"], "PASS")
        self.assertEqual(verify_quotes.verify_source_volume(pages, actual + 1)["status"], "FAIL")


class RecordTests(unittest.TestCase):
    DOC = {"source": {"work": "Future God", "author": "Alex Yamane",
                      "publisher": "Himapaan Press", "edition": "print v1.1"}}

    def _record(self):
        results = verify_quotes.verify_quotes([BODY_PAGE], [quote("Tools wait to be used", 1)])
        definitions = verify_quotes.verify_quotes(
            [HYPHEN_BREAK_PAGE], [quote("without needing external validation.", 1, "existon")]
        )
        return verify_quotes.render_verification(
            self.DOC, results, definitions, "a" * 64, 106, "b" * 64, "c" * 64
        )

    def test_record_is_byte_stable(self):
        self.assertEqual(self._record(), self._record())

    def test_record_carries_no_timestamp_or_path(self):
        record = self._record()
        self.assertNotRegex(record, r"/(?:home|Users)/[A-Za-z0-9._-]+/")
        self.assertNotRegex(record, r"\d{4}-\d{2}-\d{2}")
        self.assertNotRegex(record, r"\d{2}:\d{2}:\d{2}")

    def test_record_names_both_sources_and_the_result(self):
        record = self._record()
        self.assertIn("quotes/quotes.json` SHA-256 | `" + "b" * 64, record)
        self.assertIn("glossary/glossary.json` SHA-256 | `" + "c" * 64, record)
        self.assertIn("2 of 2 verbatim passages verified", record)
        self.assertIn("formatting alone\nis not a cryptographic attestation", record)
        self.assertIn("requires rerunning this tool", record)


if __name__ == "__main__":
    unittest.main()
