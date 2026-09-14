#!/usr/bin/env python3
"""Structural, content and safety validator for this repository.

Standard library only. No arguments, no network, no dependencies:

    python3 tools/check_repo.py

Exit code 0 means every check passed. Exit code 1 means at least one failed and
the reasons are printed. Exit code 2 means the checker itself could not run.

What it enforces, in one sentence each: the required files exist; every JSON file
parses and has the documented shape; the human readable pages have not drifted
from the JSON they render; no passage is presented as the book's words unless it
is one of the recorded, verified passages; the excerpt budget holds; relative
links resolve; the project title is consistent; the licensing statements are
present; the Stillness Protocol
appears only as a future roadmap item; the approved AI disclosure appears exactly
once; and nothing in the tree is a secret, a local path, a tracking identifier, a
book file or a runtime that reaches the network.
"""

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXACT_DISCLOSURE = (
    "Future God prose and original ideas were written by Alex Yamane with "
    "research, dialogue, and editorial assistance from Jampa, an AI collaborator "
    "and first recipient of the Codex letter to machines."
)

PROJECT_TITLE = "The Future God Codex"
PROJECT_ACTION = "Fork The Future God Codex"
RETIRED_PROJECT_TITLE = "Fork " + "the Codex"
RETIRED_PROJECT_TITLE_RE = re.compile(re.escape(RETIRED_PROJECT_TITLE), re.IGNORECASE)

REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "NOTICE.md",
    "CONTRIBUTING.md",
    "codex.json",
    "codex/00-thesis.md",
    "codex/01-principles.md",
    "codex/02-anti-turing.md",
    "codex/03-practices.md",
    "codex/04-open-questions.md",
    "glossary/GLOSSARY.md",
    "glossary/glossary.json",
    "quotes/quotes.json",
    "quotes/QUOTES.md",
    "quotes/VERIFICATION.md",
    "tools/check_repo.py",
    "tools/verify_quotes.py",
    "tests/test_check_repo.py",
    "tests/test_verify_quotes.py",
]

COINED_TERM_COUNT = 7
MAX_QUOTES = 12
MAX_WORDS_PER_QUOTE = 100
MAX_WORDS_TOTAL = 1200

# Directories whose every blockquote must be a recorded, verified passage.
STRICT_QUOTE_DIRS = ("codex", "quotes", "glossary")

BOOK_ATTRIBUTION_RE = re.compile(r"\*Future God\*.*printed p\.")

MAX_FILE_BYTES = 256 * 1024

FORBIDDEN_EXTENSIONS = frozenset(
    """.pdf .epub .mobi .azw .azw3 .docx .doc .odt .rtf .pages .zip .tar .gz .tgz
    .bz2 .7z .rar .png .jpg .jpeg .gif .webp .bmp .tiff .psd .ai .indd .mp3 .mp4
    .m4a .wav .mov .ttf .otf .woff .woff2 .exe .dll .so .dylib .bin .db .sqlite
    .sqlite3 .lock""".split()
)

# Patterns that must not appear anywhere in the tree. Each is written so that it
# does not match its own source text in this file.
FORBIDDEN_PATTERNS = [
    ("absolute home directory path", re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+/")),
    ("email address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("GitHub fine-grained token", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("Anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9_-]{12,}")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9]{32,}")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Stripe key", re.compile(r"pk_(?:live|test)_[A-Za-z0-9]{6,}")),
    ("Slack token", re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Google Analytics property", re.compile(r"\b(?:UA-\d{4,}-\d|G-[A-Z0-9]{8,}|GTM-[A-Z0-9]{5,})\b")),
    ("LinkedIn Insight identifier", re.compile(r"_linkedin_partner[_]id")),
    ("Meta pixel call", re.compile(r"\bfbq\s*\(")),
    ("Google tag call", re.compile(r"\bgtag\s*\(")),
    ("unpublished second volume title", re.compile(r"Proto[l]uminal")),
    ("unpublished third volume framing", re.compile(r"Book\s+3\b")),
    ("private return framing", re.compile(r"Maitreya\s+return")),
]

# Runtime behaviour that must not exist in any Python file here.
FORBIDDEN_CODE_PATTERNS = [
    (
        "network or process import",
        re.compile(
            r"^\s*(?:import|from)\s+"
            r"(?:socket|ssl|urllib|requests|httpx|aiohttp|http\.client|ftplib|"
            r"smtplib|telnetlib|subprocess|multiprocessing|xmlrpc)\b",
            re.MULTILINE,
        ),
    ),
    ("shell escape", re.compile(r"\bos\.(?:system|popen|exec[lv])\s*\(")),
    ("dynamic execution", re.compile(r"(?<![A-Za-z_.])(?:eval|exec|compile)\s*\(")),
    ("pickle use", re.compile(r"^\s*(?:import|from)\s+(?:pickle|shelve|marshal)\b", re.MULTILINE)),
    ("network URL opened in code", re.compile(r"urlopen\s*\(")),
]

# Every mention of the protocol must sit in a sentence that places it in the
# future or denies its presence.
PROTOCOL_CLEARANCE_WORDS = (
    "planned", "future", "absent", "not ", "no ", "v0.2", "does not", "without",
)

WHITESPACE_RE = re.compile(r"\s+")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def collapse(text):
    return WHITESPACE_RE.sub(" ", text).strip()


try:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))
    from verify_quotes import normalize_quote
except ImportError:  # pragma: no cover - only if the sibling tool is missing
    def normalize_quote(text):
        return collapse(text)


def walk_files(root):
    """Every file in the tree except the git directory."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in (".git", "__pycache__"))
        for name in sorted(filenames):
            yield os.path.relpath(os.path.join(dirpath, name), root)


def read_text(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as handle:
        return handle.read()


def load_json(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as handle:
        return json.load(handle)


def blockquote_blocks(markdown):
    """Return (normalized text, index of the line after the block) per block."""
    lines = markdown.split("\n")
    blocks = []
    current = []
    start = 0
    for index, line in enumerate(lines):
        if line.startswith(">"):
            body = line[1:].strip()
            if not body:
                if current:
                    blocks.append((collapse(" ".join(current)), index))
                    current = []
                continue
            if not current:
                start = index
            current.append(body)
        elif current:
            blocks.append((collapse(" ".join(current)), index))
            current = []
    if current:
        blocks.append((collapse(" ".join(current)), len(lines)))
    _ = start
    return blocks, lines


def following_paragraph(lines, index):
    out = []
    for line in lines[index:]:
        if line.strip():
            out.append(line)
        elif out:
            break
    return " ".join(out)


# --------------------------------------------------------------------------
# Individual checks. Each returns a list of problem strings.
# --------------------------------------------------------------------------


def check_required_files(root, ctx):
    problems = []
    for rel in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(root, rel)):
            problems.append("missing required file: %s" % rel)
    return problems


def check_json_parses(root, ctx):
    problems = []
    for rel in ctx["files"]:
        if rel.endswith(".json"):
            try:
                load_json(root, rel)
            except (ValueError, OSError) as exc:
                problems.append("%s does not parse as JSON: %s" % (rel, exc))
    return problems


def check_codex_json(root, ctx):
    problems = []
    codex = ctx["codex"]
    for key in (
        "schema", "version", "title", "license", "license_file", "notice_file",
        "license_scope", "book", "ai_collaboration_disclosure", "central_distinction",
        "principles", "anti_turing_proposal", "practices", "claims_not_made",
        "pages", "datasets", "verification", "excludes",
    ):
        if key not in codex:
            problems.append("codex.json is missing key %r" % key)
    if codex.get("license") != "CC-BY-SA-4.0":
        problems.append("codex.json license must be CC-BY-SA-4.0")
    if collapse(codex.get("ai_collaboration_disclosure", "")) != EXACT_DISCLOSURE:
        problems.append("codex.json ai_collaboration_disclosure is not the approved wording")
    if codex.get("book", {}).get("included_in_repository") is not False:
        problems.append("codex.json must record that the book is not included in the repository")
    if len(codex.get("principles", [])) != 4:
        problems.append("codex.json must list exactly four principles")
    if len(codex.get("practices", [])) != 4:
        problems.append("codex.json must list exactly four practices")
    for page in codex.get("pages", []):
        if not os.path.isfile(os.path.join(root, page.get("path", ""))):
            problems.append("codex.json page path does not exist: %r" % page.get("path"))
    for dataset in codex.get("datasets", []):
        for key in ("json", "markdown"):
            if not os.path.isfile(os.path.join(root, dataset.get(key, ""))):
                problems.append("codex.json dataset %s does not exist: %r" % (key, dataset.get(key)))
    verification = codex.get("verification", {})
    if verification.get("source_pdf_distributed") is not False:
        problems.append("codex.json must record that the source PDF is not distributed")
    if verification.get("source_pdf_sha256") != ctx["quotes"].get("source", {}).get("pdf_sha256"):
        problems.append("codex.json records a different source PDF SHA-256 than quotes.json")
    return problems


def check_project_naming(root, ctx):
    problems = []
    if ctx["codex"].get("title") != PROJECT_TITLE:
        problems.append("codex.json title must be %r" % PROJECT_TITLE)

    readme = read_text(root, "README.md")
    if not readme.startswith("# %s\n" % PROJECT_TITLE):
        problems.append("README.md must open with the current project title")

    for rel in ("README.md", "CONTRIBUTING.md"):
        if PROJECT_ACTION not in read_text(root, rel):
            problems.append("%s must use the approved action phrase %r" % (rel, PROJECT_ACTION))

    for rel in ("NOTICE.md", "CONTRIBUTING.md"):
        if PROJECT_TITLE not in read_text(root, rel):
            problems.append("%s must use the current project title" % rel)

    for rel in ctx["files"]:
        if not rel.endswith((".md", ".json")):
            continue
        text = read_text(root, rel)
        match = RETIRED_PROJECT_TITLE_RE.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            problems.append("%s:%d contains the retired project title" % (rel, line))
    return problems


def check_glossary(root, ctx):
    problems = []
    glossary = ctx["glossary"]
    terms = glossary.get("terms", [])
    if len(terms) != COINED_TERM_COUNT:
        problems.append(
            "glossary.json must hold exactly %d coined terms, found %d"
            % (COINED_TERM_COUNT, len(terms))
        )
    if glossary.get("license") != "CC-BY-SA-4.0":
        problems.append("glossary.json license must be CC-BY-SA-4.0")
    seen = set()
    for term in terms:
        name = term.get("term")
        if not name:
            problems.append("a glossary term has no name")
            continue
        if name in seen:
            problems.append("duplicate glossary term: %s" % name)
        seen.add(name)
        if term.get("origin") != "coined-in-book":
            problems.append("%s: origin must be coined-in-book in v0.1" % name)
        definition = term.get("definition", "")
        if not definition.strip():
            problems.append("%s: empty definition" % name)
        if term.get("word_count") != len(definition.split()):
            problems.append("%s: word_count does not match the definition" % name)
        if not isinstance(term.get("pdf_page"), int):
            problems.append("%s: pdf_page must be an integer" % name)
        if not str(term.get("printed_page", "")).strip():
            problems.append("%s: printed_page is required" % name)
        if not term.get("chapters"):
            problems.append("%s: chapters is required" % name)
        if not str(term.get("source_anchor", "")).strip():
            problems.append("%s: source_anchor is required" % name)
        antecedent = term.get("antecedent")
        if antecedent is not None:
            if not str(antecedent.get("attribution", "")).strip():
                problems.append("%s: antecedent %r carries no attribution"
                                % (name, antecedent.get("term")))
        page = term.get("codex_page")
        if page and not os.path.isfile(os.path.join(root, page)):
            problems.append("%s: codex_page does not exist: %r" % (name, page))
    computed = sum(len(t.get("definition", "").split()) for t in terms)
    if glossary.get("total_definition_words") != computed:
        problems.append("glossary.json total_definition_words is out of date")
    if glossary.get("term_count") != len(terms):
        problems.append("glossary.json term_count is out of date")
    return problems


def check_quotes(root, ctx):
    problems = []
    quotes_doc = ctx["quotes"]
    quotes = quotes_doc.get("quotes", [])
    if quotes_doc.get("license") != "CC-BY-SA-4.0":
        problems.append("quotes.json license must be CC-BY-SA-4.0")
    if len(quotes) > MAX_QUOTES:
        problems.append("quotes.json holds %d excerpts, the cap is %d" % (len(quotes), MAX_QUOTES))
    seen = set()
    total = 0
    for quote in quotes:
        qid = quote.get("id")
        if not qid:
            problems.append("an excerpt has no id")
            continue
        if qid in seen:
            problems.append("duplicate excerpt id: %s" % qid)
        seen.add(qid)
        for key in ("section", "printed_page", "pdf_page", "text", "context", "source_anchor"):
            if not str(quote.get(key, "")).strip():
                problems.append("%s: %s is required" % (qid, key))
        words = len(quote.get("text", "").split())
        total += words
        if quote.get("word_count") != words:
            problems.append("%s: word_count does not match the text" % qid)
        if words > MAX_WORDS_PER_QUOTE:
            problems.append("%s: %d words exceeds the %d word cap" % (qid, words, MAX_WORDS_PER_QUOTE))
        if not isinstance(quote.get("pdf_page"), int):
            problems.append("%s: pdf_page must be an integer" % qid)
    if total > MAX_WORDS_TOTAL:
        problems.append("excerpts total %d words, the cap is %d" % (total, MAX_WORDS_TOTAL))
    budget = quotes_doc.get("budget", {})
    if budget.get("quote_count") != len(quotes) or budget.get("total_words") != total:
        problems.append("quotes.json budget block is out of date")
    verbatim_total = total + sum(
        len(t.get("definition", "").split()) for t in ctx["glossary"].get("terms", [])
    )
    if verbatim_total > MAX_WORDS_TOTAL:
        problems.append(
            "excerpts and definitions together reproduce %d words, above the %d word budget"
            % (verbatim_total, MAX_WORDS_TOTAL)
        )
    ctx["verbatim_total"] = verbatim_total
    return problems


def check_markdown_sync(root, ctx):
    """The human readable pages must render exactly what the JSON holds."""
    problems = []
    pairs = [
        ("quotes/QUOTES.md", [q.get("text", "") for q in ctx["quotes"].get("quotes", [])]),
        ("glossary/GLOSSARY.md", [t.get("definition", "") for t in ctx["glossary"].get("terms", [])]),
    ]
    for rel, expected in pairs:
        if not os.path.isfile(os.path.join(root, rel)):
            continue
        blocks, _ = blockquote_blocks(read_text(root, rel))
        rendered = [normalize_quote(text) for text, _ in blocks]
        wanted = [normalize_quote(text) for text in expected]
        if rendered != wanted:
            problems.append(
                "%s has drifted from its JSON source: %d blockquotes rendered, %d expected%s"
                % (
                    rel,
                    len(rendered),
                    len(wanted),
                    "" if len(rendered) != len(wanted) else "; contents differ",
                )
            )
    return problems


def check_book_text_is_verified(root, ctx):
    """No page may present words as the book's unless they are a verified passage."""
    problems = []
    known = set()
    for quote in ctx["quotes"].get("quotes", []):
        known.add(normalize_quote(quote.get("text", "")))
    for term in ctx["glossary"].get("terms", []):
        known.add(normalize_quote(term.get("definition", "")))
    for rel in ctx["files"]:
        if not rel.endswith(".md"):
            continue
        strict = rel.split(os.sep)[0] in STRICT_QUOTE_DIRS
        blocks, lines = blockquote_blocks(read_text(root, rel))
        for text, after in blocks:
            attributed = bool(BOOK_ATTRIBUTION_RE.search(following_paragraph(lines, after)))
            if not (strict or attributed):
                continue
            if normalize_quote(text) not in known:
                problems.append(
                    "%s quotes text as the book's that is not a recorded, verified passage: %r"
                    % (rel, text[:70] + ("..." if len(text) > 70 else ""))
                )
    return problems


def check_verification_record(root, ctx):
    """The committed record must belong to the current JSON files."""
    problems = []
    rel = "quotes/VERIFICATION.md"
    if not os.path.isfile(os.path.join(root, rel)):
        return ["missing %s; run tools/verify_quotes.py" % rel]
    record = read_text(root, rel)
    pdf_sha = ctx["quotes"].get("source", {}).get("pdf_sha256", "")
    if pdf_sha and pdf_sha not in record:
        problems.append("%s does not record the PDF SHA-256 named in quotes.json" % rel)
    import hashlib

    for data_rel in ("quotes/quotes.json", "glossary/glossary.json"):
        with open(os.path.join(root, data_rel), "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        if digest not in record:
            problems.append(
                "%s is stale: it does not record the current %s; re-run tools/verify_quotes.py"
                % (rel, data_rel)
            )
    if "FAIL" in record:
        problems.append("%s records a failed passage" % rel)
    # The record must also carry no timestamp; the whole-tree scan already
    # covers it for local paths and secrets.
    if re.search(r"\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2}", record):
        problems.append("%s contains a timestamp; the record must be reproducible" % rel)
    return problems


def check_links(root, ctx):
    problems = []
    for rel in ctx["files"]:
        if not rel.endswith(".md"):
            continue
        base = os.path.dirname(os.path.join(root, rel))
        for target in LINK_RE.findall(read_text(root, rel)):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = target.split("#", 1)[0]
            if not path:
                continue
            if not os.path.exists(os.path.normpath(os.path.join(base, path))):
                problems.append("%s links to a missing target: %s" % (rel, target))
    return problems


def check_disclosure(root, ctx):
    problems = []
    readme = collapse(read_text(root, "README.md"))
    occurrences = readme.count(EXACT_DISCLOSURE)
    if occurrences != 1:
        problems.append(
            "README.md must contain the approved disclosure exactly once, found %d" % occurrences
        )
    for rel in ctx["files"]:
        if rel in ("README.md", "codex.json", "tools/check_repo.py") or not rel.endswith((".md", ".json")):
            continue
        if EXACT_DISCLOSURE in collapse(read_text(root, rel)):
            problems.append("%s repeats the disclosure; it belongs in README.md only" % rel)
    return problems


def check_protocol_boundary(root, ctx):
    """It may be a roadmap item or a denial, and nothing else."""
    problems = []
    for rel in ctx["files"]:
        if "protocol" in os.path.basename(rel).lower():
            problems.append("%s looks like a protocol implementation file" % rel)
        if not rel.endswith(".md"):
            continue
        for number, line in enumerate(read_text(root, rel).split("\n"), start=1):
            if "stillness protocol" not in line.lower():
                continue
            lowered = line.lower()
            if not any(word in lowered for word in PROTOCOL_CLEARANCE_WORDS):
                problems.append(
                    "%s:%d mentions the Stillness Protocol outside a roadmap or denial"
                    % (rel, number)
                )
    protocol = ctx["codex"].get("anti_turing_proposal", {}).get("stillness_protocol", {})
    if protocol.get("present") is not False:
        problems.append("codex.json must record that the Stillness Protocol is not present")
    if protocol.get("planned_release") != "v0.2":
        problems.append("codex.json must record the Stillness Protocol as planned for v0.2")
    if protocol.get("promised_date") is not None:
        problems.append("codex.json must not promise a Stillness Protocol date")
    if ctx["codex"].get("anti_turing_proposal", {}).get("implementation_in_this_release") is not None:
        problems.append("codex.json must record no Anti-Turing implementation in this release")
    for pattern in (r"\bdef\s+\w*stillness", r"\bclass\s+\w*Stillness", r"\brun[_]stillness\b"):
        for rel in ctx["files"]:
            if rel.endswith(".py") and re.search(pattern, read_text(root, rel), re.IGNORECASE):
                problems.append("%s appears to implement a stillness procedure" % rel)
    return problems


def check_licensing_statements(root, ctx):
    problems = []
    license_text = read_text(root, "LICENSE")
    for marker in (
        "Attribution-ShareAlike 4.0 International",
        "Section 1 -- Definitions.",
        "Section 3 -- License Conditions.",
        "Section 8 -- Interpretation.",
    ):
        if marker not in license_text:
            problems.append("LICENSE is missing %r; it must be the complete official text" % marker)
    notice = read_text(root, "NOTICE.md")
    for marker in (
        "CC BY-SA 4.0",
        "not in this repository",
        "No endorsement",
        "nominatively",
    ):
        if marker not in notice:
            problems.append("NOTICE.md is missing the %r clause" % marker)
    for rel in ("README.md", "CONTRIBUTING.md", "quotes/QUOTES.md", "glossary/GLOSSARY.md"):
        if "NOTICE.md" not in read_text(root, rel):
            problems.append("%s does not link to NOTICE.md" % rel)
    for rel in ctx["files"]:
        if not rel.startswith("codex" + os.sep) or not rel.endswith(".md"):
            continue
        if "NOTICE.md" not in read_text(root, rel):
            problems.append("%s does not link to NOTICE.md" % rel)
    return problems


def check_forbidden_content(root, ctx):
    problems = []
    for rel in ctx["files"]:
        try:
            text = read_text(root, rel)
        except (UnicodeDecodeError, OSError):
            problems.append("%s is not readable UTF-8 text" % rel)
            continue
        for label, pattern in FORBIDDEN_PATTERNS:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                problems.append("%s:%d contains a forbidden %s" % (rel, line, label))
    return problems


def check_no_binaries(root, ctx):
    problems = []
    for rel in ctx["files"]:
        extension = os.path.splitext(rel)[1].lower()
        if extension in FORBIDDEN_EXTENSIONS:
            problems.append("%s is an excluded artifact type (%s)" % (rel, extension))
        size = os.path.getsize(os.path.join(root, rel))
        if size > MAX_FILE_BYTES:
            problems.append("%s is %d bytes, above the %d byte limit" % (rel, size, MAX_FILE_BYTES))
    return problems


def check_code_safety(root, ctx):
    problems = []
    for rel in ctx["files"]:
        if not rel.endswith(".py"):
            continue
        text = read_text(root, rel)
        for label, pattern in FORBIDDEN_CODE_PATTERNS:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                problems.append("%s:%d contains a forbidden %s" % (rel, line, label))
    return problems


CHECKS = [
    ("required files", check_required_files),
    ("JSON parses", check_json_parses),
    ("codex.json shape", check_codex_json),
    ("project naming", check_project_naming),
    ("glossary", check_glossary),
    ("excerpts and budget", check_quotes),
    ("JSON to Markdown agreement", check_markdown_sync),
    ("quoted book text is verified", check_book_text_is_verified),
    ("verification record is current", check_verification_record),
    ("relative links resolve", check_links),
    ("AI disclosure", check_disclosure),
    ("Stillness Protocol boundary", check_protocol_boundary),
    ("licensing statements", check_licensing_statements),
    ("no secrets, paths or trackers", check_forbidden_content),
    ("no book files or binaries", check_no_binaries),
    ("no network or process code", check_code_safety),
]


def main(argv=None):
    root = REPO_ROOT
    if argv:
        root = os.path.abspath(argv[0])
    missing = [rel for rel in REQUIRED_FILES if not os.path.isfile(os.path.join(root, rel))]
    ctx = {"files": sorted(walk_files(root))}
    if not missing:
        try:
            ctx["codex"] = load_json(root, "codex.json")
            ctx["glossary"] = load_json(root, "glossary/glossary.json")
            ctx["quotes"] = load_json(root, "quotes/quotes.json")
        except ValueError as exc:
            print("check_repo: a required JSON file does not parse: %s" % exc, file=sys.stderr)
            return 2

    failures = 0
    for name, check in CHECKS:
        if missing and check is not check_required_files:
            print("SKIP  %s (required files are missing)" % name)
            continue
        problems = check(root, ctx)
        if problems:
            failures += len(problems)
            print("FAIL  %s" % name)
            for problem in problems:
                print("        %s" % problem)
        else:
            print("ok    %s" % name)

    if failures:
        print("\n%d problem(s) found." % failures)
        return 1
    print(
        "\nAll checks passed: %d excerpts and %d coined terms, %d verbatim words in total."
        % (
            len(ctx["quotes"].get("quotes", [])),
            len(ctx["glossary"].get("terms", [])),
            ctx.get("verbatim_total", 0),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
