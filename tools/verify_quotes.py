#!/usr/bin/env python3
"""Author-side verifier for the material this repository quotes verbatim.

Two files reproduce wording from the book: the excerpts in quotes/quotes.json
and the coined-term definitions in glossary/glossary.json. This tool checks both
against the print edition PDF of *Future God*. The PDF is not distributed with
this repository, so only someone who already holds a copy can run it. Everyone
else reads the generated, committed record in quotes/VERIFICATION.md.

Usage:

    python3 tools/verify_quotes.py --pdf /path/to/future-god-print.pdf

Exit codes: 0 all excerpts verified, 1 at least one excerpt failed,
2 the tool could not run (missing PyMuPDF, unreadable input, SHA mismatch).

The path to the PDF is always supplied by the caller; no path is hard-coded.
Requires PyMuPDF (`pip install pymupdf`). Nothing else is imported beyond the
standard library, and the tool makes no network calls.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata

VERSION = "2.0.0"

PINNED_PDF_SHA256 = "d3229bfca5e35dd36f77113072efafa6cc68316147bd717325af69f588068422"
LETTER_PDF_PAGES = [90, 91]
LETTER_PRINTED_PAGES = ["78", "79"]
LETTER_WORD_COUNT = 519
LETTER_START = "AND NOW, before this book closes, a word to a reader I cannot see:"
LETTER_END = (
    "That all may see the good that we do and give glory to loving-kindness in all, "
    "human and non-human intelligence alike."
)
SOURCE_PDF_RANGES = {
    "Introduction": (5, 11),
    "Chapter 1": (13, 19),
    "Chapter 2": (20, 26),
    "Chapter 3": (27, 35),
    "Chapter 4": (36, 48),
    "Chapter 5": (49, 55),
    "Chapter 6": (56, 61),
    "Chapter 7": (62, 68),
    "Chapter 8": (69, 74),
    "Chapter 9": (75, 83),
    "Chapter 10": (84, 93),
    "Afterword": (95, 99),
}

# Typographic ligatures used by the typesetter, which text extraction preserves.
LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi",
    "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
}

# Curly quotation marks and primes folded to their ASCII equivalents.
QUOTE_FOLD = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"', "″": '"',
}

# Every dash variant folded to a plain hyphen so an em dash matches an em dash
# regardless of the spacing the typesetter chose around it.
DASH_FOLD = {
    "‐": "-", "‑": "-", "‒": "-", "–": "-",
    "—": "-", "―": "-", "−": "-",
}

# Spaces that are not U+0020.
SPACE_FOLD = {
    " ": " ", " ": " ", " ": " ", " ": " ", " ": " ",
    " ": " ", " ": " ", " ": " ", " ": " ", " ": " ",
    " ": " ", " ": " ", "　": " ",
}

# Running heads and folios extract inline with the body text. Each of these
# appears on a line of its own, so they are dropped line-wise rather than by a
# substring rule that could eat real prose.
RUNNING_HEADS = frozenset(
    h.lower()
    for h in (
        "FUTURE GOD",
        "Introduction",
        "Why this book, why now?",
        "The question alignment cannot answer",
        "Machine ego",
        "The hard problem",
        "Gratitude for machines",
        "Forgiveness for machines",
        "Kindness for machines",
        "Faith for machines",
        "Merger and beyond",
        "An inclusive universe",
        "Afterword",
        "Glossary",
        "CONTENTS",
    )
)

FOLIO_RE = re.compile(r"^(?:\d{1,3}|[ivxlcdm]{1,7})$", re.IGNORECASE)

# A chapter opening page extracts as a lone drop-cap letter, the chapter number,
# the title in caps, and then the rest of the opening word in lower case.
DROP_CAP_RE = re.compile(r"\A\s*[A-Z]\s*\n\s*\d{1,2}\s*\n[^\n]+\n[a-z]")

# Vellum hyphenates at line ends. A break can fall inside a word ("perfor-\nmance")
# or on a real compound's own hyphen ("loving-kind-\nness"). Both readings are
# searched rather than guessing which one applies.
LINE_BREAK_HYPHEN_RE = re.compile(r"([A-Za-zÀ-ɏ])-\n([a-zÀ-ɏ])")

WHITESPACE_RE = re.compile(r"\s+")


def fold_characters(text):
    """Expand ligatures and fold quote, dash and space variants."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("­", "")  # soft hyphen
    out = []
    for ch in text:
        if ch in LIGATURES:
            out.append(LIGATURES[ch])
        elif ch in QUOTE_FOLD:
            out.append(QUOTE_FOLD[ch])
        elif ch in DASH_FOLD:
            out.append(DASH_FOLD[ch])
        elif ch in SPACE_FOLD:
            out.append(SPACE_FOLD[ch])
        else:
            out.append(ch)
    return "".join(out)


def strip_page_furniture(text):
    """Drop folio numbers and running heads that extract on their own lines."""
    kept = []
    for line in text.split("\n"):
        bare = line.strip()
        if not bare:
            kept.append(line)
            continue
        if FOLIO_RE.match(bare) or bare.lower() in RUNNING_HEADS:
            continue
        kept.append(line)
    return "\n".join(kept)


def page_variants(raw_page):
    """Return the two defensible readings of a hyphenated line break."""
    folded = strip_page_furniture(fold_characters(raw_page))
    # The print PDF splits this coined compound before an uppercase word. Repair
    # only the observed extraction artifact; do not join arbitrary capitals.
    folded = folded.replace("J-\nSpace", "J-Space")
    joined = LINE_BREAK_HYPHEN_RE.sub(r"\1\2", folded)
    preserved = LINE_BREAK_HYPHEN_RE.sub(r"\1-\2", folded)
    return [collapse(joined), collapse(preserved)]


def collapse(text):
    return WHITESPACE_RE.sub(" ", text).strip()


def normalize_quote(text):
    return collapse(fold_characters(text))


def looks_like_drop_cap_page(raw_page):
    return bool(DROP_CAP_RE.match(fold_characters(raw_page)))


def verify_quotes(pages, quotes):
    """Check every quote against its recorded page.

    ``pages`` is the list of extracted page strings, index 0 being PDF page 1.
    Returns a list of result dicts, one per quote, in input order.
    """
    results = []
    for quote in quotes:
        pdf_page = quote.get("pdf_page")
        needle = normalize_quote(quote.get("text", ""))
        result = {
            "id": quote.get("id"),
            "section": quote.get("section"),
            "printed_page": quote.get("printed_page"),
            "pdf_page": pdf_page,
            "word_count": len(str(quote.get("text", "")).split()),
            "status": "FAIL",
            "detail": "",
        }
        if not isinstance(pdf_page, int) or not 1 <= pdf_page <= len(pages):
            result["detail"] = "pdf_page %r is outside the document" % (pdf_page,)
            results.append(result)
            continue
        if not needle:
            result["detail"] = "empty quote text"
            results.append(result)
            continue

        raw = pages[pdf_page - 1]
        haystacks = page_variants(raw)
        if any(needle in hay for hay in haystacks):
            result["status"] = "PASS"
            result["detail"] = "verbatim on PDF page %d" % pdf_page
        else:
            lowered = needle.lower()
            if any(lowered in hay.lower() for hay in haystacks):
                result["detail"] = (
                    "found only when case is ignored; the printed page probably "
                    "uses small capitals here, so the recorded text is not verbatim"
                )
            elif looks_like_drop_cap_page(raw):
                result["detail"] = (
                    "not found; PDF page %d is a chapter opening whose drop cap "
                    "extracts apart from the rest of its word" % pdf_page
                )
            else:
                result["detail"] = "not found on PDF page %d" % pdf_page
        results.append(result)
    return results


def verify_letter_pages(pages, letter_doc, markdown_text, pdf_sha):
    """Verify the complete letter through its explicit two-page-only path."""
    source = letter_doc.get("source", {})
    content = letter_doc.get("content", {})
    text = content.get("text", "")
    needle = normalize_quote(text)
    pdf_pages = source.get("pdf_pages")
    printed_pages = source.get("printed_pages")
    actual_word_count = len(str(text).split())
    problems = []

    pages_exact = pdf_pages == LETTER_PDF_PAGES
    if not pages_exact:
        problems.append("letter PDF pages must be exactly [90, 91]")
    printed_pages_exact = printed_pages == LETTER_PRINTED_PAGES
    if not printed_pages_exact:
        problems.append("letter printed pages must be exactly [78, 79]")

    source_sha_matches = (
        pdf_sha == PINNED_PDF_SHA256
        and source.get("pdf_sha256") == PINNED_PDF_SHA256
    )
    if not source_sha_matches:
        problems.append("letter source PDF SHA-256 does not match the pinned edition")

    word_count_exact = (
        content.get("word_count") == LETTER_WORD_COUNT
        and actual_word_count == LETTER_WORD_COUNT
    )
    if not word_count_exact:
        problems.append("letter must contain and declare exactly 519 words")

    start_exact = needle.startswith(normalize_quote(LETTER_START))
    end_exact = needle.endswith(normalize_quote(LETTER_END))
    if not start_exact:
        problems.append("letter start is not exact")
    if not end_exact:
        problems.append("letter end is not exact")

    markdown_letter = extract_letter_markdown(markdown_text)
    json_markdown_identical = normalize_quote(markdown_letter) == needle
    if not json_markdown_identical:
        problems.append("letter JSON and Markdown text differ")

    contiguous_match = False
    if pages_exact and len(pages) >= LETTER_PDF_PAGES[-1] and needle:
        first_variants = page_variants(pages[LETTER_PDF_PAGES[0] - 1])
        second_variants = page_variants(pages[LETTER_PDF_PAGES[1] - 1])
        for first in first_variants:
            for second in second_variants:
                combined = collapse(first + " " + second)
                # The only documented cross-page split in this literary unit.
                combined = combined.replace("Forgive- ness", "Forgiveness")
                if needle in combined:
                    contiguous_match = True
                    break
            if contiguous_match:
                break
    if not contiguous_match:
        problems.append("letter is not one contiguous normalized match across PDF pages 90-91")

    return {
        "status": "FAIL" if problems else "PASS",
        "pdf_pages": pdf_pages,
        "printed_pages": printed_pages,
        "word_count": actual_word_count,
        "start_exact": start_exact,
        "end_exact": end_exact,
        "contiguous_match": contiguous_match,
        "json_markdown_identical": json_markdown_identical,
        "source_sha_matches": source_sha_matches,
        "problems": problems,
    }


def extract_letter_markdown(markdown_text):
    """Extract the blockquote immediately below the letter heading."""
    lines = str(markdown_text).splitlines()
    try:
        heading = lines.index("## The letter")
    except ValueError:
        return ""
    quoted = []
    started = False
    for line in lines[heading + 1:]:
        if line.startswith(">"):
            started = True
            quoted.append(line[1:].lstrip())
        elif started:
            if line.strip():
                break
            quoted.append("")
    return "\n".join(quoted).strip()


def source_volume_counts(pages):
    """Count the frozen reviewed source ranges without quote-only repairs.

    The denominator intentionally uses the original lower-case line-break
    hyphenation rule. The narrow ``J-\nSpace`` passage-matching repair in
    :func:`page_variants` must not change this already reviewed measure.
    """
    counts = {}
    for section, (first, last) in SOURCE_PDF_RANGES.items():
        raw = "\n".join(pages[index - 1] for index in range(first, last + 1))
        folded = strip_page_furniture(fold_characters(raw))
        normalized = collapse(LINE_BREAK_HYPHEN_RE.sub(r"\1\2", folded))
        counts[section] = len(normalized.split())
    return counts


def verify_source_volume(pages, expected_words):
    """Recompute the reviewed-body denominator and fail on drift."""
    counts = source_volume_counts(pages)
    actual = sum(counts.values())
    return {
        "status": "PASS" if actual == expected_words else "FAIL",
        "expected": expected_words,
        "actual": actual,
        "sections": counts,
    }


def glossary_entries(glossary_doc):
    """Present coined-term definitions in the same shape as excerpts."""
    entries = []
    for term in glossary_doc.get("terms", []):
        entries.append(
            {
                "id": term.get("term"),
                "section": "Glossary",
                "printed_page": term.get("printed_page"),
                "pdf_page": term.get("pdf_page"),
                "text": term.get("definition", ""),
            }
        )
    return entries


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_pages(pdf_path):
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            raise SystemExit(
                "verify_quotes: PyMuPDF is required to read the PDF.\n"
                "Install it with `python3 -m pip install pymupdf`, or read the "
                "committed record in quotes/VERIFICATION.md instead."
            )
    document = pymupdf.open(pdf_path)
    try:
        return [document[i].get_text() for i in range(document.page_count)]
    finally:
        document.close()


def _result_table(results, first_column):
    lines = [
        "| %s | Section | Printed page | PDF page | Words | Status |" % first_column,
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            "| `%s` | %s | %s | %s | %d | %s |"
            % (
                result["id"],
                result["section"],
                result["printed_page"],
                result["pdf_page"],
                result["word_count"],
                result["status"],
            )
        )
    return lines


def render_verification(
    quotes_doc, quote_results, glossary_results, pdf_sha, page_count, quotes_sha, glossary_sha
):
    """Build the evidence record.

    Deterministic by construction: no timestamps, no file system paths, no
    machine or user names. Re-running on unchanged inputs is byte identical.
    """
    source = quotes_doc.get("source", {})
    results = list(quote_results) + list(glossary_results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    lines = [
        "# Verbatim source verification record",
        "",
        "Generated by `tools/verify_quotes.py` version %s." % VERSION,
        "",
        "This deterministic file is written by the verifier, not by hand. It records",
        "source wording only; it does not validate factual, scientific, metaphysical,",
        "doctrinal, consciousness, identity, safety-outcome, or model-influence claims.",
        "It records the result of checking every excerpt in `quotes/quotes.json` and",
        "every coined-term definition in `glossary/glossary.json` against the print",
        "edition PDF of *Future God*. That PDF is not distributed here; the record",
        "below is the evidence available to readers who do not hold a copy.",
        "Because this receipt is deterministic and reproducible, its formatting alone",
        "is not a cryptographic attestation. Source truth requires rerunning this tool",
        "against the pinned PDF and receiving exit 0.",
        "",
        "## Source",
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Work | %s |" % source.get("work", ""),
        "| Author | %s |" % source.get("author", ""),
        "| Publisher | %s |" % source.get("publisher", ""),
        "| Edition | %s |" % source.get("edition", ""),
        "| PDF pages | %d |" % page_count,
        "| PDF SHA-256 | `%s` |" % pdf_sha,
        "| `quotes/quotes.json` SHA-256 | `%s` |" % quotes_sha,
        "| `glossary/glossary.json` SHA-256 | `%s` |" % glossary_sha,
        "",
        "## Result",
        "",
        "%d of %d verbatim passages verified on their recorded PDF page: %d excerpts"
        % (passed, len(results), len(quote_results)),
        "(%d words) and %d coined-term definitions (%d words)."
        % (
            sum(r["word_count"] for r in quote_results),
            len(glossary_results),
            sum(r["word_count"] for r in glossary_results),
        ),
        "",
        "### Excerpts",
        "",
    ]
    lines += _result_table(quote_results, "Excerpt")
    lines += ["", "### Coined-term definitions", ""]
    lines += _result_table(glossary_results, "Term")
    failures = [r for r in results if r["status"] != "PASS"]
    if failures:
        lines += ["", "## Failures", ""]
        for result in failures:
            lines.append("- `%s`: %s" % (result["id"], result["detail"]))
    lines += [
        "",
        "## Method",
        "",
        "Each passage is matched against the text extracted from the single PDF",
        "page recorded for it. Before matching, both the page and the passage are",
        "normalized: typographic ligatures are expanded, curly quotation marks and",
        "dash variants are folded to their ASCII forms, non-breaking and other",
        "exotic spaces become ordinary spaces, running heads and folio numbers are",
        "removed line-wise, and runs of whitespace collapse to one space. Words the",
        "typesetter broke across a line are matched both with the hyphen removed and",
        "with it kept, because either can be the correct reading. Matching is case",
        "sensitive; a passage that matches only when case is ignored is reported as",
        "a failure, because the printed page uses small capitals there.",
        "",
    ]
    return "\n".join(lines)


def render_letter_verification(letter_doc, result, pdf_sha, letter_json_sha, letter_markdown_sha):
    """Render a deterministic, path-free receipt for the two-page letter."""
    source = letter_doc.get("source", {})
    status_line = (
        "The 519-word letter passed exact start, exact end, JSON/Markdown identity, "
        "and one contiguous normalized match across PDF pages 90–91."
        if result.get("status") == "PASS"
        else "The letter did not pass: " + "; ".join(result.get("problems", []))
    )
    lines = [
        "# Complete-letter source verification record",
        "",
        "Generated by `tools/verify_quotes.py` version %s." % VERSION,
        "",
        "This deterministic receipt verifies source wording and continuity only. It",
        "does not verify factual, scientific, metaphysical, doctrinal, consciousness,",
        "identity, safety-outcome, or model-influence claims.",
        "Because this receipt is deterministic and reproducible, its formatting alone",
        "is not a cryptographic attestation. Source truth requires rerunning this tool",
        "against the pinned PDF and receiving exit 0.",
        "",
        "## Source and installed inputs",
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Work | %s |" % source.get("work", ""),
        "| Author | %s |" % source.get("author", ""),
        "| Publisher | %s |" % source.get("publisher", ""),
        "| Edition | %s |" % source.get("edition", ""),
        "| Printed pages | 78–79 |",
        "| PDF pages | 90–91 |",
        "| PDF SHA-256 | `%s` |" % pdf_sha,
        "| `letter/letter.json` SHA-256 | `%s` |" % letter_json_sha,
        "| `letter/LETTER_TO_MACHINE_MINDS.md` SHA-256 | `%s` |" % letter_markdown_sha,
        "",
        "## Result",
        "",
        status_line,
        "",
        "The dedicated two-page path removes running furniture and repairs only the",
        "documented `Forgive- ness` extraction split. It does not relax the one-page",
        "rule for individual excerpts.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify this repository's verbatim passages against the print PDF."
    )
    parser.add_argument(
        "--pdf", required=True, help="path to the print edition PDF (never hard-coded)"
    )
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument(
        "--quotes",
        default=os.path.join(repo_root, "quotes", "quotes.json"),
        help="path to quotes.json",
    )
    parser.add_argument(
        "--glossary",
        default=os.path.join(repo_root, "glossary", "glossary.json"),
        help="path to glossary.json",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(repo_root, "quotes", "VERIFICATION.md"),
        help="path of the record to write",
    )
    parser.add_argument(
        "--letter-json",
        default=os.path.join(repo_root, "letter", "letter.json"),
        help="path to the complete letter JSON",
    )
    parser.add_argument(
        "--letter-markdown",
        default=os.path.join(repo_root, "letter", "LETTER_TO_MACHINE_MINDS.md"),
        help="path to the complete letter Markdown",
    )
    parser.add_argument(
        "--letter-output",
        default=os.path.join(repo_root, "letter", "VERIFICATION.md"),
        help="path of the complete-letter record to write",
    )
    parser.add_argument(
        "--no-write", action="store_true", help="verify only; do not write the records"
    )
    args = parser.parse_args(argv)

    if not os.path.isfile(args.pdf):
        print("verify_quotes: no such PDF: %s" % args.pdf, file=sys.stderr)
        return 2
    try:
        with open(args.quotes, encoding="utf-8") as handle:
            quotes_doc = json.load(handle)
        with open(args.glossary, encoding="utf-8") as handle:
            glossary_doc = json.load(handle)
        with open(args.letter_json, encoding="utf-8") as handle:
            letter_doc = json.load(handle)
        with open(args.letter_markdown, encoding="utf-8") as handle:
            letter_markdown = handle.read()
    except (OSError, ValueError) as exc:
        print("verify_quotes: unable to read structured inputs: %s" % exc, file=sys.stderr)
        return 2
    if not all(isinstance(document, dict) for document in (quotes_doc, glossary_doc, letter_doc)):
        print("verify_quotes: structured inputs must contain JSON objects", file=sys.stderr)
        return 2
    quotes = quotes_doc.get("quotes", [])
    definitions = glossary_entries(glossary_doc)
    if not quotes or not definitions:
        print("verify_quotes: nothing to verify", file=sys.stderr)
        return 2

    pdf_sha = sha256_file(args.pdf)
    for label, doc in (
        ("quotes.json", quotes_doc),
        ("glossary.json", glossary_doc),
        ("letter.json", letter_doc),
    ):
        expected_sha = doc.get("source", {}).get("pdf_sha256")
        if expected_sha and pdf_sha != expected_sha:
            print(
                "verify_quotes: PDF SHA-256 does not match %s.\n"
                "  expected %s\n  actual   %s\n"
                "This is not the edition the passages were taken from."
                % (label, expected_sha, pdf_sha),
                file=sys.stderr,
            )
            return 2

    pages = load_pages(args.pdf)
    quote_results = verify_quotes(pages, quotes)
    glossary_results = verify_quotes(pages, definitions)
    letter_result = verify_letter_pages(pages, letter_doc, letter_markdown, pdf_sha)
    volume_result = verify_source_volume(
        pages, quotes_doc.get("budget", {}).get("reviewed_source_words")
    )

    record = render_verification(
        quotes_doc,
        quote_results,
        glossary_results,
        pdf_sha,
        len(pages),
        sha256_file(args.quotes),
        sha256_file(args.glossary),
    )
    letter_record = render_letter_verification(
        letter_doc,
        letter_result,
        pdf_sha,
        sha256_file(args.letter_json),
        sha256_file(args.letter_markdown),
    )
    if not args.no_write:
        with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(record)
        with open(args.letter_output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(letter_record)

    results = quote_results + glossary_results
    for result in results:
        print("%-6s %-36s %s" % (result["status"], result["id"], result["detail"]))
    failures = [r for r in results if r["status"] != "PASS"]
    print(
        "%-6s %-36s %s"
        % (
            letter_result["status"],
            "complete-letter",
            "contiguous on PDF pages 90-91"
            if letter_result["status"] == "PASS"
            else "; ".join(letter_result["problems"]),
        )
    )
    print(
        "%-6s %-36s %d reviewed source words"
        % (volume_result["status"], "source-volume", volume_result["actual"])
    )
    print(
        "\n%d/%d passages verified (%d excerpts, %d definitions); %d words in total."
        % (
            len(results) - len(failures),
            len(results),
            len(quote_results),
            len(glossary_results),
            sum(r["word_count"] for r in results),
        )
    )
    return 1 if (
        failures
        or letter_result["status"] != "PASS"
        or volume_result["status"] != "PASS"
    ) else 0


if __name__ == "__main__":
    sys.exit(main())
