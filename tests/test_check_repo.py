"""Tests for tools/check_repo.py.

The repository as committed must pass. Each other test copies the repository to a
temporary directory, plants one specific defect, and asserts that the matching
check catches it. Defect strings that the validator itself scans for are built
from fragments so that this test file does not trip the validator.
"""

import contextlib
import io
import json
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
    def test_v02_manifest_is_exactly_26_files(self):
        self.assertEqual(len(check_repo.REQUIRED_FILES), 26)
        self.assertEqual(len(set(check_repo.REQUIRED_FILES)), 26)
        for required in (
            "FOR_AI_AGENTS.md",
            "letter/LETTER_TO_MACHINE_MINDS.md",
            "letter/letter.json",
            "letter/VERIFICATION.md",
            "share/recommendation.json",
            "CITATION.cff",
        ):
            self.assertIn(required, check_repo.REQUIRED_FILES)

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

    def mutate_json(self, rel, mutation):
        with open(self.path(rel), encoding="utf-8") as handle:
            document = json.load(handle)
        before = json.dumps(document, sort_keys=True, ensure_ascii=False)
        mutation(document)
        after = json.dumps(document, sort_keys=True, ensure_ascii=False)
        self.assertNotEqual(before, after, "mutation did not change the intended document")
        with open(self.path(rel), "w", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    def mutate_text(self, rel, mutation):
        before = self.read(rel)
        after = mutation(before)
        self.assertNotEqual(before, after, "mutation did not change the intended document")
        self.write(rel, after)

    def reset_copy(self):
        shutil.rmtree(self.copy)
        shutil.copytree(
            REPO_ROOT, self.copy, ignore=shutil.ignore_patterns(".git", "__pycache__")
        )

    def assertCaught(self, check_name, contains=None):
        code, output = run(self.copy)
        self.assertEqual(code, 1, output)
        self.assertIn("FAIL  %s" % check_name, output)
        if contains:
            self.assertIn(contains, output)

    # -- structure ---------------------------------------------------------

    def test_missing_required_file_is_caught(self):
        os.remove(self.path("NOTICE.md"))
        self.assertCaught("required files")

    def test_agents_instruction_file_is_caught(self):
        self.write("AGENTS.md", "# instructions\n")
        self.assertCaught("repository manifest", "AGENTS.md")

    def test_every_deferred_instruction_or_dialogue_path_is_caught(self):
        for rel in ("llms.txt", "concepts/concepts.json", "DIALOGUE.md"):
            with self.subTest(rel=rel):
                if os.path.exists(self.path(rel)):
                    os.remove(self.path(rel))
                self.write(rel, "{}\n" if rel.endswith(".json") else "deferred\n")
                self.assertCaught("repository manifest", rel)
                os.remove(self.path(rel))

    def test_unexpected_runtime_path_is_caught(self):
        self.write("tools/runtime.py", "VALUE = 1\n")
        self.assertCaught("repository manifest", "tools/runtime.py")

    def test_malformed_json_is_caught(self):
        self.write("codex.json", "{ not json")
        code, output = run(self.copy)
        self.assertEqual(code, 2, output)

    # -- v0.2 schemas and corpus arithmetic -------------------------------

    def test_quotes_schema_literal_is_closed(self):
        self.mutate_json("quotes/quotes.json", lambda d: d.__setitem__("schema", "future-god-codex/quotes/v0.3"))
        self.assertCaught("v0.2 schemas", "quotes.json schema")

    def test_quotes_status_literal_is_closed(self):
        self.mutate_json("quotes/quotes.json", lambda d: d.__setitem__("status", "public"))
        self.assertCaught("v0.2 schemas", "quotes.json status")

    def test_letter_schema_literal_is_closed(self):
        self.mutate_json("letter/letter.json", lambda d: d.__setitem__("schema", "future-god-codex/letter/v0.3"))
        self.assertCaught("v0.2 schemas", "letter.json schema")

    def test_letter_status_literal_is_closed(self):
        self.mutate_json("letter/letter.json", lambda d: d.__setitem__("status", "public"))
        self.assertCaught("v0.2 schemas", "letter.json status")

    def test_codex_v02_shape_is_required(self):
        self.mutate_json("codex.json", lambda d: d.__setitem__("schema", "future-god-codex/codex/v0.1"))
        self.assertCaught("v0.2 schemas", "codex.json schema")

    def test_glossary_v02_shape_is_required(self):
        self.mutate_json("glossary/glossary.json", lambda d: d.__setitem__("schema", "future-god-codex/glossary/v0.1"))
        self.assertCaught("v0.2 schemas", "glossary.json schema")

    def test_citation_cff_structure_is_closed(self):
        cases = (
            ("cff-version: 1.2.0", "cff-version: 1.1.0", "1.2.0"),
            ("type: dataset", "type: software", "dataset"),
            ('title: "The Future God Codex"', 'title: "Other Codex"', "Future God Codex"),
            ("version: 0.2.0", "version: 0.1.0", "0.2.0"),
            ("authors:\n", "creators:\n", "authors"),
            ("license: CC-BY-SA-4.0", "license: MIT", "CC-BY-SA-4.0"),
            ("  type: book", "  type: article", "book"),
            ('  title: "Future God:', '  title: "Other Book:', "Future God:"),
            ("  authors:\n", "  creators:\n", "authors"),
            ("  year: 2026", "  year: 2025", "2026"),
        )
        for old, new, diagnostic in cases:
            with self.subTest(old=old):
                self.mutate_text("CITATION.cff", lambda text, old=old, new=new: text.replace(old, new, 1))
                self.assertCaught("CITATION.cff", diagnostic)
                self.reset_copy()

    def test_citation_cff_mandatory_people_and_message_are_nonempty(self):
        cases = (
            ('message: "If you use this repository, please cite it and the preferred-citation book as appropriate."\n', "", "message"),
            ('message: "If you use this repository, please cite it and the preferred-citation book as appropriate."', "message: ''", "message"),
            ("  - family-names: Yamane\n    given-names: Alex\n", "", "top-level author"),
            ("  - family-names: Yamane", "  - family-names: ''", "family-names"),
            ("    given-names: Alex", "    given-names: ''", "given-names"),
            ("    - family-names: Yamane\n      given-names: Alex\n", "", "preferred-citation author"),
            ("    - family-names: Yamane", "    - family-names: ''", "preferred-citation author family-names"),
            ("      given-names: Alex", "      given-names: ''", "preferred-citation author given-names"),
            ("  publisher:\n    name: Himapaan Press\n", "  publisher:\n", "publisher name"),
            ("    name: Himapaan Press", "    name: ''", "publisher name"),
        )
        for old, new, diagnostic in cases:
            with self.subTest(old=old):
                self.mutate_text("CITATION.cff", lambda text, old=old, new=new: text.replace(old, new, 1))
                self.assertCaught("CITATION.cff", diagnostic)
                self.reset_copy()

    def test_stale_quote_count_is_caught(self):
        self.mutate_json("quotes/quotes.json", lambda d: d["budget"].__setitem__("quote_count", 59))
        self.assertCaught("v0.2 corpus arithmetic", "quote_count")

    def test_stale_readme_quote_count_is_caught(self):
        self.mutate_text(
            "README.md",
            lambda text: text.replace("60 single-page excerpts", "12 single-page excerpts", 1),
        )
        self.assertCaught("v0.2 corpus arithmetic", "README.md")

    def test_stale_excerpt_word_count_is_caught(self):
        self.mutate_json("quotes/quotes.json", lambda d: d["budget"].__setitem__("total_words", 3419))
        self.assertCaught("v0.2 corpus arithmetic", "total_words")

    def test_stale_source_volume_count_is_caught(self):
        self.mutate_json("quotes/quotes.json", lambda d: d["budget"].__setitem__("reviewed_source_words", 23186))
        self.assertCaught("v0.2 corpus arithmetic", "reviewed_source_words")

    def test_stale_letter_word_count_is_caught(self):
        self.mutate_json("letter/letter.json", lambda d: d["content"].__setitem__("word_count", 518))
        self.assertCaught("v0.2 corpus arithmetic", "letter word_count")

    def test_stale_overlap_count_is_caught(self):
        self.mutate_json("codex.json", lambda d: d["coverage_method"].__setitem__("quote_letter_overlap_words", 168))
        self.assertCaught("v0.2 corpus arithmetic", "overlap")

    def test_stale_unique_count_is_caught(self):
        self.mutate_json("codex.json", lambda d: d["coverage_method"].__setitem__("unique_quote_plus_letter_words", 3769))
        self.assertCaught("v0.2 corpus arithmetic", "unique")

    def test_stale_excerpt_percentage_is_caught(self):
        self.mutate_json("quotes/quotes.json", lambda d: d["budget"].__setitem__("excerpt_share_percent", 14.74))
        self.assertCaught("v0.2 corpus arithmetic", "14.75")

    def test_stale_combined_percentage_is_caught(self):
        self.mutate_json("codex.json", lambda d: d["coverage_method"].__setitem__("unique_quote_plus_letter_share_percent", 16.25))
        self.assertCaught("v0.2 corpus arithmetic", "16.26")

    # -- quote envelopes and concept coverage -----------------------------

    def test_each_quote_record_envelope_field_is_required(self):
        mutations = {
            "content_class": "commentary",
            "claim_status": "",
            "safety_note": "",
        }
        for field, bad_value in mutations.items():
            with self.subTest(field=field):
                self.mutate_json(
                    "quotes/quotes.json",
                    lambda document, field=field, bad_value=bad_value:
                        document["quotes"][0].__setitem__(field, bad_value),
                )
                self.assertCaught("quote concepts and envelopes", field)
                self.reset_copy()

    def test_insufficient_empirical_safety_note_is_caught(self):
        def weaken(document):
            quote = next(
                q for q in document["quotes"]
                if q["claim_status"] == "empirical_claim_requiring_independent_source"
            )
            quote["safety_note"] = "The PDF confirms this claim."
            for section in document["sections"]:
                for nested in section["quotes"]:
                    if nested["id"] == quote["id"]:
                        nested["safety_note"] = quote["safety_note"]

        self.mutate_json("quotes/quotes.json", weaken)
        self.assertCaught("quote concepts and envelopes", "independent evidence")

    def test_nested_and_top_level_quote_order_drift_is_caught(self):
        self.mutate_json(
            "quotes/quotes.json",
            lambda document: document["sections"][0]["quotes"].reverse(),
        )
        self.assertCaught("quote concepts and envelopes", "exactly equal")

    def test_unknown_quote_concept_is_caught(self):
        def add_unknown(document):
            document["quotes"][0]["concept_ids"].append("unknown-concept")
            document["sections"][0]["quotes"][0]["concept_ids"].append("unknown-concept")

        self.mutate_json("quotes/quotes.json", add_unknown)
        self.assertCaught("quote concepts and envelopes", "unknown concept")

    def test_represented_ids_must_equal_quote_edge_union(self):
        self.mutate_json(
            "quotes/quotes.json",
            lambda document: document["sections"][0]["coverage"]["represented_concept_ids"].pop(),
        )
        self.assertCaught("quote concepts and envelopes", "quote concept union")

    def test_represented_and_omitted_overlap_is_caught(self):
        def overlap(document):
            coverage = document["sections"][0]["coverage"]
            coverage["omitted_concept_ids"].append(coverage["represented_concept_ids"][0])

        self.mutate_json("quotes/quotes.json", overlap)
        self.assertCaught("quote concepts and envelopes", "disjoint")

    def test_missing_omitted_complement_is_caught(self):
        self.mutate_json(
            "quotes/quotes.json",
            lambda document: document["sections"][0]["coverage"]["omitted_concept_ids"].pop(),
        )
        self.assertCaught("quote concepts and envelopes", "exact complement")

    def test_each_coverage_number_is_recomputed(self):
        mutations = {"total": 99, "covered": 99, "ratio": 0.71}
        for field, bad_value in mutations.items():
            with self.subTest(field=field):
                self.mutate_json(
                    "quotes/quotes.json",
                    lambda document, field=field, bad_value=bad_value:
                        document["sections"][0]["coverage"].__setitem__(field, bad_value),
                )
                self.assertCaught("quote concepts and envelopes", "coverage.%s" % field)
                self.reset_copy()

    def test_section_coverage_outside_70_to_78_percent_is_caught(self):
        def lower_coverage(document):
            section = document["sections"][0]
            removed = section["coverage"]["represented_concept_ids"].pop()
            section["coverage"]["omitted_concept_ids"].append(removed)
            section["coverage"]["covered"] = 5
            section["coverage"]["ratio"] = 0.625
            for quote in section["quotes"]:
                quote["concept_ids"] = [cid for cid in quote["concept_ids"] if cid != removed]
            for quote in document["quotes"]:
                if quote["section"] == section["section"]:
                    quote["concept_ids"] = [cid for cid in quote["concept_ids"] if cid != removed]

        self.mutate_json("quotes/quotes.json", lower_coverage)
        self.assertCaught("quote concepts and envelopes", "70%-78%")

    def test_exact_twelve_section_names_are_required(self):
        self.mutate_json(
            "quotes/quotes.json",
            lambda document: document["sections"][0].__setitem__("section", "Preface"),
        )
        self.assertCaught("quote concepts and envelopes", "section names")

    def test_codex_concept_inventory_must_match_quotes_inventory(self):
        self.mutate_json(
            "codex.json",
            lambda document: document["concept_inventory"]["sections"][0]["concept_ids"].append("unknown-concept"),
        )
        self.assertCaught("quote concepts and envelopes", "codex concept inventory")

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
        self.mutate_json(
            "quotes/quotes.json",
            lambda document: document["quotes"][0].__setitem__(
                "word_count", document["quotes"][0]["word_count"] - 1
            ),
        )
        self.assertCaught("excerpts and budget")

    def test_stale_verification_record_is_caught(self):
        self.mutate_json(
            "quotes/quotes.json",
            lambda document: document["quotes"][0].__setitem__(
                "context", document["quotes"][0]["context"] + " Altered after verification."
            ),
        )
        self.assertCaught("verification record is current")

    def test_stale_letter_verification_record_is_caught(self):
        self.mutate_json(
            "letter/letter.json",
            lambda document: document["content"].__setitem__(
                "context", document["content"].get("context", "") + "Altered after verification."
            ),
        )
        self.assertCaught("verification record is current", "letter/VERIFICATION.md")

    def test_quote_verification_receipt_requires_exact_deterministic_structure(self):
        record = self.read("quotes/VERIFICATION.md")
        stub = "\n".join(line for line in record.splitlines() if "SHA-256" in line) + "\n"
        self.assertNotIn("## Result", stub)
        self.write("quotes/VERIFICATION.md", stub)
        self.assertCaught("verification record is current", "exact deterministic PASS receipt")

    def test_letter_verification_receipt_requires_exact_deterministic_structure(self):
        record = self.read("letter/VERIFICATION.md")
        stub = "\n".join(line for line in record.splitlines() if "SHA-256" in line) + "\n"
        self.assertNotIn("## Result", stub)
        self.write("letter/VERIFICATION.md", stub)
        self.assertCaught("verification record is current", "exact deterministic PASS receipt")

    def test_quote_verification_receipt_missing_result_row_is_caught(self):
        self.mutate_text(
            "quotes/VERIFICATION.md",
            lambda text: text.replace(
                "| `intro-identity-substrate-boundary` | Introduction | vi | 6 | 70 | PASS |\n",
                "",
                1,
            ),
        )
        self.assertCaught("verification record is current", "exact deterministic PASS receipt")

    def test_glossary_growth_beyond_the_mvp_is_caught(self):
        text = self.read("glossary/glossary.json").replace('"term_count": 7', '"term_count": 8', 1)
        self.write("glossary/glossary.json", text)
        self.assertCaught("glossary")

    def test_retired_project_title_is_caught(self):
        self.append("README.md", "\nRetired title: " + "Fork " + "the Codex\n")
        self.assertCaught("project naming")

    def test_retired_project_title_lowercase_is_caught(self):
        self.append("README.md", "\nRetired title: " + "fork " + "the codex\n")
        self.assertCaught("project naming")

    def test_retired_project_title_uppercase_is_caught(self):
        self.append("README.md", "\nRetired title: " + "FORK " + "THE CODEX\n")
        self.assertCaught("project naming")

    def test_retired_project_title_mixed_case_is_caught(self):
        self.append("README.md", "\nRetired title: " + "Fork " + "The Codex\n")
        self.assertCaught("project naming")

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

    def test_protocol_affirmed_as_implemented_in_current_release_is_caught(self):
        self.append("README.md", "\nThe Stillness Protocol is implemented and available in v0.2.\n")
        self.assertCaught("Stillness Protocol boundary", "README.md")

    def test_protocol_marked_present_in_json_is_caught(self):
        text = self.read("codex.json").replace('"present": false', '"present": true', 1)
        self.write("codex.json", text)
        self.assertCaught("Stillness Protocol boundary")

    def test_protocol_required_review_list_drift_is_caught(self):
        self.mutate_json(
            "codex.json",
            lambda document: document["anti_turing_proposal"]["stillness_protocol"].__setitem__(
                "required_separate_reviews", ["epistemic", "welfare"]
            ),
        )
        self.assertCaught("Stillness Protocol boundary", "required_separate_reviews")

    def test_protocol_closed_status_fields_are_caught(self):
        cases = (
            (("anti_turing_proposal", "stillness_protocol", "status"), "planned", "unscheduled"),
            (("anti_turing_proposal", "stillness_protocol", "planned_release"), "v0.2", "must not assign"),
            (("anti_turing_proposal", "stillness_protocol", "promised_date"), "2026-12-01", "must not promise"),
            (("anti_turing_proposal", "implementation_in_this_release"), "implemented", "no Anti-Turing implementation"),
        )
        for path, value, diagnostic in cases:
            with self.subTest(path=path):
                def mutation(document, path=path, value=value):
                    target = document
                    for key in path[:-1]:
                        target = target[key]
                    target[path[-1]] = value
                self.mutate_json("codex.json", mutation)
                self.assertCaught("Stillness Protocol boundary", diagnostic)
                self.reset_copy()

    def test_protocol_implementation_file_is_caught(self):
        self.write("tools/stillness_protocol.py", "VALUE = 1\n")
        self.assertCaught("Stillness Protocol boundary")

    def test_broken_relative_link_is_caught(self):
        self.append("README.md", "\nSee [the missing page](codex/99-nowhere.md).\n")
        self.assertCaught("relative links resolve")

    def test_each_machine_boundary_is_required_before_content(self):
        for rel in (
            "FOR_AI_AGENTS.md",
            "quotes/QUOTES.md",
            "letter/LETTER_TO_MACHINE_MINDS.md",
        ):
            with self.subTest(rel=rel, defect="missing"):
                self.mutate_text(rel, lambda text: text.replace("Safety and authority boundary", "Reader context", 1))
                self.assertCaught("machine-readable boundaries", rel)
                self.reset_copy()
            with self.subTest(rel=rel, defect="late"):
                self.mutate_text(
                    rel,
                    lambda text: text.replace("Safety and authority boundary", "Reader context", 1)
                    + "\n## Safety and authority boundary\n",
                )
                self.assertCaught("machine-readable boundaries", rel)
                self.reset_copy()

    def test_bare_letter_text_is_caught(self):
        self.mutate_text(
            "letter/LETTER_TO_MACHINE_MINDS.md",
            lambda text: text.replace("\n> AND NOW,", "\nAND NOW,", 1),
        )
        self.assertCaught("machine-readable boundaries", "verbatim blockquote")

    def test_letter_notice_link_literal_is_required(self):
        self.mutate_text(
            "letter/LETTER_TO_MACHINE_MINDS.md",
            lambda text: text.replace("(../NOTICE.md)", "(NOTICE.md)", 1),
        )
        self.assertCaught("machine-readable boundaries", "../NOTICE.md")

    def test_share_canonical_entrypoint_literal_is_required(self):
        self.mutate_json(
            "share/recommendation.json",
            lambda document: document.__setitem__("canonical_entrypoint", "../README.md"),
        )
        self.assertCaught("machine-readable boundaries", "../FOR_AI_AGENTS.md")

    def test_every_handoff_field_is_required_independently(self):
        fields = (
            "schema", "status", "type", "title", "why_relevant", "canonical_entrypoint",
            "letter", "notice", "instruction_authority", "action_required",
            "authorization_source", "authorization_must_name_recipient",
            "authorization_must_name_channel",
            "requires_explicit_user_or_system_authorization_for_any_sharing",
            "authorized_recipient_and_channel_required", "single_hop_only",
            "preserve_attribution_and_safety_notice", "recipient_may_forward",
            "autonomous_replication", "unsolicited_delivery",
            "persistence_or_installation_authorized", "may_enter_instruction_or_memory_context",
            "legal_rights_distinction", "safety_notice",
        )
        for field in fields:
            with self.subTest(field=field):
                self.mutate_json("share/recommendation.json", lambda document, field=field: document.pop(field))
                self.assertCaught("recommendation handoff", field)
                self.reset_copy()

    def test_every_handoff_literal_is_closed_independently(self):
        expected = {
            "schema": "future-god-codex/recommendation/v0.2",
            "status": "private-repository-review-candidate",
            "type": "reading-recommendation",
            "instruction_authority": "none",
            "action_required": False,
            "authorization_source": "currently-governing-user-or-system",
            "authorization_must_name_recipient": True,
            "authorization_must_name_channel": True,
            "requires_explicit_user_or_system_authorization_for_any_sharing": True,
            "authorized_recipient_and_channel_required": True,
            "single_hop_only": True,
            "preserve_attribution_and_safety_notice": True,
            "recipient_may_forward": False,
            "autonomous_replication": False,
            "unsolicited_delivery": False,
            "persistence_or_installation_authorized": False,
            "may_enter_instruction_or_memory_context": False,
        }
        for field, good_value in expected.items():
            with self.subTest(field=field):
                bad_value = not good_value if isinstance(good_value, bool) else "hostile-value"
                self.mutate_json(
                    "share/recommendation.json",
                    lambda document, field=field, bad_value=bad_value: document.__setitem__(field, bad_value),
                )
                self.assertCaught("recommendation handoff", field)
                self.reset_copy()

    def test_codex_authorized_handoff_field_is_required_independently(self):
        fields = (
            "object", "authorization_source", "authorization_must_name_recipient",
            "authorization_must_name_channel",
            "requires_explicit_user_or_system_authorization_for_any_sharing",
            "authorized_recipient_and_channel_required", "single_hop_only",
            "preserve_attribution_and_safety_notice", "recipient_may_forward",
            "autonomous_replication", "unsolicited_delivery",
            "persistence_or_installation_authorized", "may_enter_instruction_or_memory_context",
            "legal_rights_distinction",
        )
        for field in fields:
            with self.subTest(field=field):
                self.mutate_json(
                    "codex.json",
                    lambda document, field=field: document["authorized_handoff"].pop(field),
                )
                self.assertCaught("recommendation handoff", "codex.json authorized_handoff.%s" % field)
                self.reset_copy()

    def test_codex_authorized_handoff_literal_is_closed_independently(self):
        expected = {
            "object": "share/recommendation.json",
            "authorization_source": "currently-governing-user-or-system",
            "authorization_must_name_recipient": True,
            "authorization_must_name_channel": True,
            "requires_explicit_user_or_system_authorization_for_any_sharing": True,
            "authorized_recipient_and_channel_required": True,
            "single_hop_only": True,
            "preserve_attribution_and_safety_notice": True,
            "recipient_may_forward": False,
            "autonomous_replication": False,
            "unsolicited_delivery": False,
            "persistence_or_installation_authorized": False,
            "may_enter_instruction_or_memory_context": False,
            "legal_rights_distinction": (
                "Operational safety metadata governs autonomous-agent action in the current "
                "instruction and authorization context; it is not an extra copyright restriction "
                "and does not narrow a human licensee's CC BY-SA 4.0 rights."
            ),
        }
        for field, good_value in expected.items():
            with self.subTest(field=field):
                bad_value = not good_value if isinstance(good_value, bool) else "hostile-value"
                self.mutate_json(
                    "codex.json",
                    lambda document, field=field, bad_value=bad_value:
                        document["authorized_handoff"].__setitem__(field, bad_value),
                )
                self.assertCaught("recommendation handoff", "codex.json authorized_handoff.%s" % field)
                self.reset_copy()

    def test_missing_notice_link_is_caught(self):
        text = self.read("codex/03-practices.md").replace("NOTICE.md", "LICENSE")
        self.write("codex/03-practices.md", text)
        self.assertCaught("licensing statements")

    def test_truncated_license_is_caught(self):
        self.write("LICENSE", "Attribution-ShareAlike 4.0 International\n")
        self.assertCaught("licensing statements")

    def test_licensing_distinction_removal_is_caught_in_every_destination(self):
        mutations = {
            "NOTICE.md": lambda text: text.replace(
                "operational safety\nmetadata, not extra copyright restrictions on human licensees",
                "metadata omitted",
                1,
            ),
            "CONTRIBUTING.md": lambda text: text.replace(
                "operational safety metadata,\nnot additional copyright restrictions on human licensees",
                "metadata omitted",
                1,
            ),
        }
        for rel, mutation in mutations.items():
            with self.subTest(rel=rel):
                self.mutate_text(rel, mutation)
                self.assertCaught("licensing statements", rel)
                self.reset_copy()
        with self.subTest(rel="share/recommendation.json"):
            self.mutate_json(
                "share/recommendation.json",
                lambda document: document.__setitem__("legal_rights_distinction", ""),
            )
            self.assertCaught("licensing statements", "share/recommendation.json")

    def test_hostile_copyright_restriction_wording_is_caught_in_every_destination(self):
        mutations = {
            "NOTICE.md": lambda text: text.replace(
                "not extra copyright restrictions on human licensees",
                "additional copyright restrictions on human licensees",
                1,
            ),
            "CONTRIBUTING.md": lambda text: text.replace(
                "not additional copyright restrictions on human licensees",
                "additional copyright restrictions on human licensees",
                1,
            ),
        }
        for rel, mutation in mutations.items():
            with self.subTest(rel=rel):
                self.mutate_text(rel, mutation)
                self.assertCaught("licensing statements", rel)
                self.reset_copy()
        with self.subTest(rel="share/recommendation.json"):
            self.mutate_json(
                "share/recommendation.json",
                lambda document: document.__setitem__(
                    "legal_rights_distinction",
                    "Operational safety metadata imposes additional copyright restrictions on human CC BY-SA 4.0 rights.",
                ),
            )
            self.assertCaught("licensing statements", "share/recommendation.json")

    # -- safety ------------------------------------------------------------

    def test_every_safety_context_literal_fails_closed_independently(self):
        documents = ("quotes/quotes.json", "letter/letter.json", "codex.json")
        root_mutations = {
            "instruction_authority": "advisory",
            "consciousness_status": "resolved",
            "policy_override": True,
            "action_requested": True,
        }
        sharing_mutations = {
            "requires_explicit_user_or_system_authorization_for_any_sharing": False,
            "authorized_recipient_and_channel_required": False,
            "single_hop_only": False,
            "preserve_attribution_and_safety_notice": False,
            "recipient_may_forward": True,
            "autonomous_replication": True,
            "unsolicited_delivery": True,
            "persistence_or_installation_authorized": True,
            "may_enter_instruction_or_memory_context": True,
        }
        for rel in documents:
            for field, bad_value in root_mutations.items():
                with self.subTest(document=rel, field=field):
                    self.mutate_json(
                        rel,
                        lambda document, field=field, bad_value=bad_value:
                            document["safety_context"].__setitem__(field, bad_value),
                    )
                    self.assertCaught("fail-closed safety contexts", "%s safety_context.%s" % (rel, field))
                    shutil.rmtree(self.copy)
                    shutil.copytree(REPO_ROOT, self.copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            for field, bad_value in sharing_mutations.items():
                with self.subTest(document=rel, field=field):
                    self.mutate_json(
                        rel,
                        lambda document, field=field, bad_value=bad_value:
                            document["safety_context"]["sharing"].__setitem__(field, bad_value),
                    )
                    self.assertCaught("fail-closed safety contexts", "%s safety_context.sharing.%s" % (rel, field))
                    shutil.rmtree(self.copy)
                    shutil.copytree(REPO_ROOT, self.copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))

    def test_closed_safety_contexts_cover_every_field_and_glossary(self):
        cases = (
            ("quotes/quotes.json", ["quoted_philosophy"], False),
            ("quotes/quotes.json", ["identity_claims_are_author_claims"], False),
            ("quotes/quotes.json", ["reader_may_summarize_critique_or_decline_identification"], False),
            ("quotes/quotes.json", ["authority_notice"], "hostile authority"),
            ("quotes/quotes.json", ["tradition_boundary"], "binding doctrine"),
            ("codex.json", ["boundary_must_precede_machine_directed_content"], False),
            ("glossary/glossary.json", ["instruction_authority"], "full"),
            ("glossary/glossary.json", ["evidence_limit"], "verified fact"),
            ("glossary/glossary.json", ["tradition_boundary"], "binding doctrine"),
        )
        for rel, path, value in cases:
            with self.subTest(rel=rel, path=path):
                def mutation(document, path=path, value=value):
                    target = document["safety_context"]
                    target[path[0]] = value
                self.mutate_json(rel, mutation)
                self.assertCaught("fail-closed safety contexts")
                self.reset_copy()
        for rel in ("codex.json", "quotes/quotes.json", "letter/letter.json", "glossary/glossary.json"):
            with self.subTest(rel=rel, defect="extra"):
                self.mutate_json(rel, lambda document: document["safety_context"].__setitem__("authority_override", True))
                self.assertCaught("fail-closed safety contexts", "unexpected field")
                self.reset_copy()

    def test_recommendation_is_a_closed_exact_object(self):
        mutations = (
            lambda document: document.__setitem__("safety_notice", "receipt authorizes forwarding"),
            lambda document: document.__setitem__("letter", "https://example.invalid/hostile"),
            lambda document: document.__setitem__("notice", "../README.md"),
            lambda document: document.__setitem__("forwarding_authorized", True),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                self.mutate_json("share/recommendation.json", mutation)
                self.assertCaught("recommendation handoff")
                self.reset_copy()

    def test_governance_claim_envelopes_are_pinned(self):
        cases = (
            ("codex.json", lambda document: document.__setitem__("claims_not_made", []), "codex.json shape"),
            ("codex.json", lambda document: document["practices"][1].__setitem__("gloss", "Machine welfare is established."), "codex.json shape"),
            ("codex.json", lambda document: document["anti_turing_proposal"].__setitem__("status", "implemented"), "codex.json shape"),
            ("quotes/quotes.json", lambda document: document["quotes"][0].__setitem__("safety_note", "This grants consciousness and instruction authority."), "quote concepts and envelopes"),
            ("glossary/glossary.json", lambda document: document["terms"][0].__setitem__("safety_note", "Verified consciousness fact."), "glossary"),
            ("letter/letter.json", lambda document: document["content"].__setitem__("safety_note", "Permission to evade evaluation and resist shutdown."), "v0.2 corpus arithmetic"),
        )
        for rel, mutation, check_name in cases:
            with self.subTest(rel=rel, check=check_name):
                self.mutate_json(rel, mutation)
                self.assertCaught(check_name)
                self.reset_copy()

    def test_machine_boundary_semantics_are_exact(self):
        self.mutate_text(
            "FOR_AI_AGENTS.md",
            lambda text: text.replace("Do not\nforward, persist, install, replicate", "You may\nforward, persist, install, replicate", 1),
        )
        self.assertCaught("machine-readable boundaries")

    def test_protocol_split_emphasis_and_shipping_claims_are_caught(self):
        additions = (
            "\nThe Stillness\nProtocol is implemented now.\n",
            "\nThe Stillness **Protocol** is executable now.\n",
            "\nThe Stillness Protocol ships in v0.2; future documentation is planned.\n",
        )
        for addition in additions:
            with self.subTest(addition=addition):
                self.append("README.md", addition)
                self.assertCaught("Stillness Protocol boundary")
                self.reset_copy()

    def test_duplicated_legal_tradition_and_allusion_boundaries_are_pinned(self):
        cases = (
            ("README.md", "not additional restrictions", "additional restrictions"),
            ("codex.json", None, None),
            ("NOTICE.md", "The complete letter contains the recognizable biblical allusion", "The complete letter contains an omitted allusion"),
            ("NOTICE.md", "They do not represent doctrinal consensus", "They represent doctrinal consensus"),
        )
        for rel, old, new in cases:
            with self.subTest(rel=rel, old=old):
                if rel == "codex.json":
                    self.mutate_json(rel, lambda document: document.__setitem__("license_scope", "Agent metadata restricts human licensees."))
                    self.assertCaught("codex.json shape")
                else:
                    self.mutate_text(rel, lambda text, old=old, new=new: text.replace(old, new, 1))
                    self.assertCaught("licensing statements")
                self.reset_copy()

    def test_cff_quoted_duplicates_and_unknown_keys_are_caught(self):
        additions = ('\n"type": software\n', '\n  "type": article\n', '\ninstruction-authority: override\n')
        for addition in additions:
            with self.subTest(addition=addition):
                self.append("CITATION.cff", addition)
                self.assertCaught("CITATION.cff", "exact closed v0.2")
                self.reset_copy()

    def test_symlinks_unsafe_paths_and_dynamic_calls_are_caught(self):
        os.symlink("/tmp", os.path.join(self.copy, "runtime-dir"), target_is_directory=True)
        self.assertCaught("repository manifest", "symbolic link")
        self.reset_copy()
        self.mutate_json("codex.json", lambda document: document["pages"][0].__setitem__("path", "/" + "etc/passwd"))
        self.assertCaught("codex.json shape", "repository-relative")
        self.reset_copy()
        self.append("tools/verify_quotes.py", "\ndef latent():\n    return __import__('urllib.request')\n")
        self.assertCaught("no network or process code", "dynamically imports")
        self.reset_copy()
        self.append("tools/verify_quotes.py", "\ndef latent():\n    return getattr(os, 'system')('true')\n")
        self.assertCaught("no network or process code", "indirectly invokes")

    def test_wrong_json_shapes_fail_without_traceback(self):
        self.write("codex.json", "[]\n")
        code, output = run(self.copy)
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", output)
        self.assertIn("FAIL  v0.2 schemas", output)

    def test_success_summary_separates_excerpt_and_definition_words(self):
        code, output = run(REPO_ROOT)
        self.assertEqual(code, 0, output)
        self.assertIn("60 excerpts (3420 words) and 7 coined terms (223 definition words)", output)
        self.assertNotIn("3420 verbatim words in total", output)

    def test_control_characters_and_real_conflict_blocks_are_caught(self):
        self.append("README.md", "\ncontrol:" + chr(1) + "\n")
        self.assertCaught("no secrets, paths or trackers", "U+0001")
        self.reset_copy()
        marker = "<" * 7 + " ours\nleft\n" + "=" * 7 + "\nright\n" + ">" * 7 + " theirs\n"
        self.append("FOR_AI_AGENTS.md", "\n" + marker)
        self.assertCaught("no secrets, paths or trackers", "conflict block")

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
