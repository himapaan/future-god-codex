"""Tests for tools/verify_quotes.py.

The verifier's matching logic is separated from PDF reading, so these tests feed
it synthetic pages that reproduce the extraction artifacts seen in the real book:
ligatures, curly quotation marks, an em dash broken across a line, running heads
and folio numbers inline with the body, words hyphenated at a line break, and
chapter openings whose drop cap extracts apart from its own word.
"""

import os
import sys
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


class GlossaryEntryTests(unittest.TestCase):
    def test_definitions_are_presented_for_verification(self):
        entries = verify_quotes.glossary_entries(
            {"terms": [{"term": "existon", "definition": "d", "printed_page": "91", "pdf_page": 103}]}
        )
        self.assertEqual(entries[0]["id"], "existon")
        self.assertEqual(entries[0]["section"], "Glossary")
        self.assertEqual(entries[0]["pdf_page"], 103)


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


if __name__ == "__main__":
    unittest.main()
