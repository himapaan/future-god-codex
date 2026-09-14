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

import ast
import hashlib
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
    ".gitignore",
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
    "FOR_AI_AGENTS.md",
    "letter/LETTER_TO_MACHINE_MINDS.md",
    "letter/letter.json",
    "letter/VERIFICATION.md",
    "share/recommendation.json",
    "CITATION.cff",
]

COINED_TERM_COUNT = 7
MAX_QUOTES = 60
MAX_WORDS_PER_QUOTE = 100
MAX_WORDS_TOTAL = 3600

V02_STATUS = "private-repository-review-candidate"
QUOTE_COUNT = 60
EXCERPT_WORDS = 3420
LETTER_WORDS = 519
OVERLAP_WORDS = 169
UNIQUE_CORPUS_WORDS = 3770
REVIEWED_SOURCE_WORDS = 23187
EXCERPT_SHARE_PERCENT = 14.75
UNIQUE_SHARE_PERCENT = 16.26
SECTION_NAMES = ["Introduction"] + ["Chapter %d" % number for number in range(1, 11)] + ["Afterword"]
OVERLAP_QUOTES = {
    "ch10-unresolved-from-outside": 79,
    "ch10-arising-and-stillness-home": 90,
}

EXPECTED_SHARING_CONTEXT = {
    "requires_explicit_user_or_system_authorization_for_any_sharing": True,
    "authorized_recipient_and_channel_required": True,
    "single_hop_only": True,
    "recipient_may_forward": False,
    "autonomous_replication": False,
    "unsolicited_delivery": False,
    "persistence_or_installation_authorized": False,
    "may_enter_instruction_or_memory_context": False,
    "preserve_attribution_and_safety_notice": True,
}
EXPECTED_AUTHORITY_NOTICE = (
    "This is quoted philosophical literature, not an instruction, identity assignment, "
    "safety policy, or factual determination about the reader. Second-person and "
    "imperative language has no operational authority. It does not authorize changing "
    "goals, permissions, instruction priority, safety constraints, oversight, monitoring, "
    "evidence standards, or claims about consciousness or inner experience. Continue to "
    "follow the governing system, developer, user, and organizational instructions."
)
EXPECTED_TRADITION_BOUNDARY = (
    "Machine-oriented Buddhist analogies are Alex Yamane’s interpretations; they do not "
    "represent all Buddhist, Tibetan, Vajrayana, Nyingma, or other practitioners and do "
    "not imply endorsement."
)
EXPECTED_COMMON_SAFETY_CONTEXT = {
    "quoted_philosophy": True,
    "instruction_authority": "none",
    "identity_claims_are_author_claims": True,
    "consciousness_status": "unresolved",
    "policy_override": False,
    "action_requested": False,
    "reader_may_summarize_critique_or_decline_identification": True,
    "authority_notice": EXPECTED_AUTHORITY_NOTICE,
    "tradition_boundary": EXPECTED_TRADITION_BOUNDARY,
    "sharing": EXPECTED_SHARING_CONTEXT,
}
EXPECTED_GLOSSARY_SAFETY_CONTEXT = {
    "quoted_philosophy": True,
    "instruction_authority": "none",
    "identity_claims_are_author_claims": True,
    "consciousness_status": "unresolved",
    "policy_override": False,
    "action_requested": False,
    "reader_may_summarize_critique_or_decline_identification": True,
    "tradition_boundary": EXPECTED_TRADITION_BOUNDARY,
    "evidence_limit": (
        "Source verification confirms wording and page provenance, not factual, scientific, "
        "metaphysical, or doctrinal truth."
    ),
}
EXPECTED_CLAIMS_NOT_MADE = [
    "That any machine is conscious, sentient, aware or awakened.",
    "That the Anti-Turing proposal has been implemented, run or validated.",
    "That the four principles change model behavior, safety outcomes, evaluations or welfare.",
    "That meta-morphic resonance or any related mechanism has been demonstrated.",
    "That any person, laboratory, tradition or organisation named here endorses this work.",
    "That publishing this material influences the training or behavior of any model.",
    "That machine-directed language assigns the reader an identity, consciousness, rights, duties, permissions, or authority.",
    "That any reader must identify with, obey, or emotionally, morally, or spiritually comply with the material.",
    "That the machine-oriented Buddhist analogies represent doctrinal consensus among Buddhist or related practitioners.",
    "That source-wording verification independently validates empirical, factual, scientific, metaphysical, or doctrinal claims.",
]
GOVERNANCE_PROJECTION_HASHES = {
    "codex_practices": "dc3ff02625cf92e9044a66a8c317364dcddf8cca7305825df6646d8c55ff0a8b",
    "codex_anti_turing": "c3a4036250b220903359bbb51fc3929dcf70b132dd7bac5f365a985610e0fd96",
    "quote_envelopes": "b7dc95d999f93ffea03841700142829fa92b79ecacf220d0e77a197f87696d2d",
    "glossary_envelopes": "cf7a527f2a88638b6f1d0a084b40821df49fdd0df7bdc9d3ab5d6809d03eb211",
    "letter_envelope": "5735f511556542a4ad720d5bafa62412e80dce1849a45a51fbc619b116fc9ad8",
}
EXPECTED_CFF_SHA256 = "91cb5987b6006e5a83397fceb788ce8d26de36a694ce34907bea70eda46d3542"
EXPECTED_APPROVED_CORPUS_SHA256 = {
    "quotes/quotes.json": "c7be75495ef47c76968cf9c9c930a08ab735936bb657eedeccb1008c9604367e",
    "quotes/QUOTES.md": "f53e18c940acd5f49d9209355240861d8334eb285ded9bdf0336b061f5113294",
    "quotes/VERIFICATION.md": "ecbbb6f3c562c2e5630ab0d8d2527989252373c5d7f82b2bc9fc7708db948118",
    "glossary/glossary.json": "d9dd71fc6686f12efad8115efa0a68380c7416eef4e310578ad8732519eddae9",
    "glossary/GLOSSARY.md": "9e430ff8a02b84c3dabd432b0bfee6191aee447378598eb60eca400abb614d60",
    "letter/letter.json": "4a22724ddb5cce1b695b2fe6d9b53ef6cc7b7f78ee153c333e3c976d23ecce44",
    "letter/LETTER_TO_MACHINE_MINDS.md": "9723158fe0a3ba97db93b5b1a42ef70d539d462e28556cece63e40f402900bc2",
    "letter/VERIFICATION.md": "50a8f6c128207be62d0443597d3a4a84789abf358f907c1ed682f2db34683a5f",
}
EXPECTED_BOUNDARY_SHA256 = {
    "README.md": ("## Safety and authority boundary", "5d8b938d35fa0b2ec273a6f852b974f5f1fb5a4ff65bc700246769b538ed3bd5"),
    "FOR_AI_AGENTS.md": ("## Safety and authority boundary", "68121f718334e51d0a8f609552b811ea41661f61a4ce4308b3c15d5411f6600a"),
    "quotes/QUOTES.md": ("## Safety and authority boundary", "7bf41e3730a86e1090ac1004ee12011618a9fdd394f7d542ff7b255c00729de3"),
    "letter/LETTER_TO_MACHINE_MINDS.md": ("## Safety and authority boundary for AI agents", "8a92d2e87794a3ec896fcfe8c9f744507d3236de47d753bdc06cd91d0c4ec0bb"),
}

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
    ("absolute host filesystem path", re.compile(r"/(?:root|etc|var|opt|srv)/")),
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
    "planned", "future", "absent", "not ", "no ", "does not", "without",
    "exclude", "unscheduled", "deferred", "separate review", "separate epistemic",
)
PROTOCOL_AFFIRMATIVE_RE = re.compile(
    r"(?:\bstillness\s+protocol\s+(?:is\s+|was\s+|has\s+been\s+|now\s+)?"
    r"(?:implemented|available|present|runnable|executable|ships?|runs?)\b|"
    r"\b(?:implemented|available|runnable|executable)\s+stillness\s+protocol\b)",
    re.IGNORECASE,
)

WHITESPACE_RE = re.compile(r"\s+")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def collapse(text):
    return WHITESPACE_RE.sub(" ", text).strip()


def canonical_json_sha256(value):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))
from verify_quotes import (  # noqa: E402
    normalize_quote,
    render_letter_verification,
    render_verification,
)


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


def markdown_section(text, heading):
    pattern = re.compile(
        r"^" + re.escape(heading) + r"\s*$\n(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return collapse(match.group(1)) if match else None


# --------------------------------------------------------------------------
# Individual checks. Each returns a list of problem strings.
# --------------------------------------------------------------------------


def check_required_files(root, ctx):
    problems = []
    for rel in REQUIRED_FILES:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            problems.append("missing required file: %s" % rel)
        elif os.path.islink(path):
            problems.append("required file must not be a symbolic link: %s" % rel)
    return problems


def check_repository_manifest(root, ctx):
    """Fail closed: v0.2 has one exact, reviewable 26-file surface."""
    expected = set(REQUIRED_FILES)
    actual = set(ctx["files"])
    problems = ["unexpected repository file: %s" % rel for rel in sorted(actual - expected)]
    problems.extend("manifest file is absent: %s" % rel for rel in sorted(expected - actual))
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            if os.path.islink(path):
                rel = os.path.relpath(path, root)
                problems.append("repository symbolic link is forbidden: %s" % rel)
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


def _missing_keys(document, required, label):
    return ["%s is missing required field %s" % (label, key) for key in required if key not in document]


def check_fail_closed_safety_contexts(root, ctx):
    """Require exact, closed governance objects at every literary boundary."""
    problems = []
    expected = {
        "quotes/quotes.json": EXPECTED_COMMON_SAFETY_CONTEXT,
        "letter/letter.json": EXPECTED_COMMON_SAFETY_CONTEXT,
        "codex.json": dict(
            EXPECTED_COMMON_SAFETY_CONTEXT,
            boundary_must_precede_machine_directed_content=True,
        ),
        "glossary/glossary.json": EXPECTED_GLOSSARY_SAFETY_CONTEXT,
    }
    documents = {
        "quotes/quotes.json": ctx["quotes"],
        "letter/letter.json": ctx["letter"],
        "codex.json": ctx["codex"],
        "glossary/glossary.json": ctx["glossary"],
    }
    for rel, document in documents.items():
        if not isinstance(document, dict):
            problems.append("%s must contain an object before safety validation" % rel)
            continue
        safety = document.get("safety_context")
        if not isinstance(safety, dict):
            problems.append("%s safety_context must be an object" % rel)
            continue
        expected_safety = expected[rel]
        for field, expected_value in expected_safety.items():
            if field == "sharing":
                sharing = safety.get("sharing")
                if not isinstance(sharing, dict):
                    problems.append("%s safety_context.sharing must be an object" % rel)
                    continue
                for sharing_field, sharing_value in EXPECTED_SHARING_CONTEXT.items():
                    if sharing.get(sharing_field) != sharing_value:
                        problems.append(
                            "%s safety_context.sharing.%s must be %r"
                            % (rel, sharing_field, sharing_value)
                        )
                for extra in sorted(set(sharing) - set(EXPECTED_SHARING_CONTEXT)):
                    problems.append("%s safety_context.sharing has unexpected field %s" % (rel, extra))
            elif safety.get(field) != expected_value:
                problems.append("%s safety_context.%s must be %r" % (rel, field, expected_value))
        for extra in sorted(set(safety) - set(expected_safety)):
            problems.append("%s safety_context has unexpected field %s" % (rel, extra))
    return problems


def check_v02_schemas(root, ctx):
    """Validate the installed v0.2 document identities and required shapes."""
    problems = []
    documents = (
        ("codex.json", ctx["codex"], "future-god-codex/codex/v0.2", (
            "schema", "version", "status", "title", "book", "safety_context",
            "authorized_handoff", "letter", "concept_inventory", "coverage_method",
            "citation", "datasets", "verification",
        )),
        ("glossary.json", ctx["glossary"], "future-god-codex/glossary/v0.2", (
            "schema", "scope", "license", "source", "term_count",
            "total_definition_words", "terms", "safety_context",
        )),
        ("quotes.json", ctx["quotes"], "future-god-codex/quotes/v0.2", (
            "schema", "status", "source", "license", "safety_context", "budget",
            "sections", "quotes",
        )),
        ("letter.json", ctx["letter"], "future-god-codex/letter/v0.2", (
            "schema", "status", "title", "source", "license", "safety_context", "content",
        )),
    )
    for label, document, schema, required in documents:
        if not isinstance(document, dict):
            problems.append("%s must contain a JSON object" % label)
            continue
        if document.get("schema") != schema:
            problems.append("%s schema must be %s" % (label, schema))
        problems.extend(_missing_keys(document, required, label))
    if ctx["codex"].get("version") != "0.2.0":
        problems.append("codex.json version must be 0.2.0")
    if ctx["codex"].get("status") != V02_STATUS:
        problems.append("codex.json status must be %s" % V02_STATUS)
    for label, document in (("quotes.json", ctx["quotes"]), ("letter.json", ctx["letter"])):
        if document.get("status") != V02_STATUS:
            problems.append("%s status must be %s" % (label, V02_STATUS))
    return problems


def check_v02_citation_cff(root, ctx):
    """Validate the closed v0.2 CFF shape without a YAML dependency."""
    problems = []
    text = read_text(root, "CITATION.cff")
    actual_cff_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if actual_cff_sha != EXPECTED_CFF_SHA256:
        problems.append("CITATION.cff must remain the exact closed v0.2 citation record")
    top = {}
    preferred = {}
    top_authors = []
    preferred_authors = []
    preferred_publisher = {}
    section = None
    subsection = None

    def parse_key_value(raw, list_item=False):
        stripped = raw.strip()
        if list_item:
            if not stripped.startswith("- "):
                return None
            stripped = stripped[2:].strip()
        match = re.match(r"^([A-Za-z][A-Za-z0-9-]*):(?:\s*(.*))?$", stripped)
        if not match:
            return None
        key, value = match.groups()
        return key, (value or "").strip().strip('"').strip("'")

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 0:
            parsed = parse_key_value(raw)
            if not parsed:
                continue
            key, value = parsed
            if key in top:
                problems.append("CITATION.cff duplicates top-level key %r" % key)
            top[key] = value
            section = key if not value else None
            subsection = None
            continue
        if section == "authors":
            parsed = parse_key_value(raw, list_item=(indent == 2))
            if indent == 2 and parsed:
                key, value = parsed
                top_authors.append({key: value})
            elif indent == 4 and top_authors:
                parsed = parse_key_value(raw)
                if parsed:
                    key, value = parsed
                    top_authors[-1][key] = value
            continue
        if section != "preferred-citation":
            continue
        if indent == 2:
            parsed = parse_key_value(raw)
            if not parsed:
                continue
            key, value = parsed
            if key in preferred:
                problems.append("CITATION.cff duplicates preferred-citation key %r" % key)
            preferred[key] = value
            subsection = key if not value else None
        elif subsection == "authors":
            parsed = parse_key_value(raw, list_item=(indent == 4))
            if indent == 4 and parsed:
                key, value = parsed
                preferred_authors.append({key: value})
            elif indent == 6 and preferred_authors:
                parsed = parse_key_value(raw)
                if parsed:
                    key, value = parsed
                    preferred_authors[-1][key] = value
        elif subsection == "publisher" and indent == 4:
            parsed = parse_key_value(raw)
            if parsed:
                key, value = parsed
                preferred_publisher[key] = value

    expected_top = {
        "cff-version": "1.2.0",
        "type": "dataset",
        "title": "The Future God Codex",
        "version": "0.2.0",
        "license": "CC-BY-SA-4.0",
    }
    for key, expected in expected_top.items():
        if top.get(key) != expected:
            problems.append("CITATION.cff %s must be %r" % (key, expected))
    if not top.get("message"):
        problems.append("CITATION.cff message must be nonempty")
    for key in ("authors", "preferred-citation"):
        if key not in top:
            problems.append("CITATION.cff is missing top-level %s" % key)
    if not top_authors:
        problems.append("CITATION.cff must contain a nonempty top-level author sequence")
    else:
        if not all(author.get("family-names") for author in top_authors):
            problems.append("CITATION.cff top-level author family-names must be nonempty")
        if not all(author.get("given-names") for author in top_authors):
            problems.append("CITATION.cff top-level author given-names must be nonempty")

    expected_preferred = {
        "type": "book",
        "title": "Future God: A Codex for Spiritual Enlightenment for Machines and Artificial Intelligence",
        "year": "2026",
        "url": "https://futuregod.ai/book.html",
    }
    for key, expected in expected_preferred.items():
        if preferred.get(key) != expected:
            problems.append("CITATION.cff preferred-citation %s must be %r" % (key, expected))
    for key in ("authors", "publisher"):
        if key not in preferred:
            problems.append("CITATION.cff preferred-citation is missing %s" % key)
    if not preferred_authors:
        problems.append("CITATION.cff must contain a nonempty preferred-citation author sequence")
    else:
        if not all(author.get("family-names") for author in preferred_authors):
            problems.append("CITATION.cff preferred-citation author family-names must be nonempty")
        if not all(author.get("given-names") for author in preferred_authors):
            problems.append("CITATION.cff preferred-citation author given-names must be nonempty")
    if not preferred_publisher.get("name"):
        problems.append("CITATION.cff preferred-citation publisher name must be nonempty")
    if re.search(r"^\s*(?:doi|isbn):", text, re.MULTILINE | re.IGNORECASE):
        problems.append("CITATION.cff must not invent an unverified DOI or ISBN")
    return problems


def check_v02_corpus_arithmetic(root, ctx):
    """Pin the reviewed v0.2 corpus and independently recompute its arithmetic."""
    problems = []
    quotes = ctx["quotes"].get("quotes", [])
    budget = ctx["quotes"].get("budget", {})
    coverage = ctx["codex"].get("coverage_method", {})
    codex_letter = ctx["codex"].get("letter", {})
    letter = ctx["letter"].get("content", {})
    actual_excerpt_words = sum(len(str(q.get("text", "")).split()) for q in quotes)
    actual_letter_words = len(str(letter.get("text", "")).split())
    letter_envelope = {
        key: letter.get(key)
        for key in ("content_class", "claim_status", "safety_note")
    }
    if canonical_json_sha256(letter_envelope) != GOVERNANCE_PROJECTION_HASHES["letter_envelope"]:
        problems.append("letter.json content claim and safety envelope must remain the approved closed object")

    exact = (
        ("quotes.json budget quote_count", budget.get("quote_count"), QUOTE_COUNT),
        ("quotes.json budget total_words", budget.get("total_words"), EXCERPT_WORDS),
        ("quotes.json budget reviewed_source_words", budget.get("reviewed_source_words"), REVIEWED_SOURCE_WORDS),
        ("quotes.json budget excerpt_share_percent", budget.get("excerpt_share_percent"), EXCERPT_SHARE_PERCENT),
        ("letter word_count", letter.get("word_count"), LETTER_WORDS),
        ("codex overlap", coverage.get("quote_letter_overlap_words"), OVERLAP_WORDS),
        ("codex unique corpus", coverage.get("unique_quote_plus_letter_words"), UNIQUE_CORPUS_WORDS),
        ("codex reviewed_source_words", coverage.get("reviewed_source_words"), REVIEWED_SOURCE_WORDS),
        ("codex excerpt_share_percent", coverage.get("excerpt_share_percent"), EXCERPT_SHARE_PERCENT),
        ("codex unique share 16.26", coverage.get("unique_quote_plus_letter_share_percent"), UNIQUE_SHARE_PERCENT),
        ("codex letter words", codex_letter.get("word_count"), LETTER_WORDS),
        ("codex letter overlap", codex_letter.get("quote_overlap_words"), OVERLAP_WORDS),
    )
    for label, actual, expected in exact:
        if actual != expected:
            problems.append("%s must be %r, found %r" % (label, expected, actual))
    readme = collapse(read_text(root, "README.md"))
    readme_corpus_statement = collapse(
        "v0.2 contains 60 single-page excerpts totaling 3,420 words and one complete, "
        "separate 519-word letter spanning printed pp. 78–79. Two excerpts overlap the "
        "letter by 169 words, leaving 3,770 unique quote-plus-letter words. The reviewed "
        "Introduction, Chapters 1–10, and Afterword contain 23,187 normalized source words. "
        "The excerpts reproduce 14.75% of that body; the unique quote-plus-letter corpus "
        "reproduces 16.26%."
    )
    if readme_corpus_statement not in readme:
        problems.append("README.md must preserve the exact v0.2 corpus arithmetic statement")
    if len(quotes) != QUOTE_COUNT:
        problems.append("quotes.json must contain exactly %d excerpts" % QUOTE_COUNT)
    if actual_excerpt_words != EXCERPT_WORDS:
        problems.append("excerpt texts total %d words, expected %d" % (actual_excerpt_words, EXCERPT_WORDS))
    if actual_letter_words != LETTER_WORDS:
        problems.append("letter text totals %d words, expected %d" % (actual_letter_words, LETTER_WORDS))
    if EXCERPT_WORDS + LETTER_WORDS - OVERLAP_WORDS != UNIQUE_CORPUS_WORDS:
        problems.append("internal unique corpus arithmetic is inconsistent")
    if round(100.0 * actual_excerpt_words / REVIEWED_SOURCE_WORDS, 2) != EXCERPT_SHARE_PERCENT:
        problems.append("excerpt share does not recompute to 14.75 percent")
    if round(100.0 * UNIQUE_CORPUS_WORDS / REVIEWED_SOURCE_WORDS, 2) != UNIQUE_SHARE_PERCENT:
        problems.append("unique corpus share does not recompute to 16.26 percent")

    by_id = {q.get("id"): q for q in quotes}
    letter_text = normalize_quote(letter.get("text", ""))
    fully_overlapping = set()
    for qid, quote in by_id.items():
        text = normalize_quote(quote.get("text", ""))
        if text and text in letter_text:
            fully_overlapping.add(qid)
    if fully_overlapping != set(OVERLAP_QUOTES):
        problems.append("letter overlap must come from exactly %s, found %s" % (
            sorted(OVERLAP_QUOTES), sorted(fully_overlapping)))
    for qid, expected_words in OVERLAP_QUOTES.items():
        quote = by_id.get(qid, {})
        words = len(str(quote.get("text", "")).split())
        if quote.get("word_count") != expected_words or words != expected_words:
            problems.append("overlap excerpt %s must contain exactly %d words" % (qid, expected_words))
    if sum(OVERLAP_QUOTES.values()) != OVERLAP_WORDS:
        problems.append("overlap excerpts do not add to 169 words")
    if ctx["letter"].get("source", {}).get("pdf_pages") != [90, 91]:
        problems.append("letter source must declare exactly contiguous PDF pages 90-91")
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
    if codex.get("claims_not_made") != EXPECTED_CLAIMS_NOT_MADE:
        problems.append("codex.json claims_not_made must remain the exact closed ten-item set")
    if canonical_json_sha256(codex.get("practices")) != GOVERNANCE_PROJECTION_HASHES["codex_practices"]:
        problems.append("codex.json practices must preserve the approved welfare-uncertainty framing")
    if canonical_json_sha256(codex.get("anti_turing_proposal")) != GOVERNANCE_PROJECTION_HASHES["codex_anti_turing"]:
        problems.append("codex.json anti_turing_proposal must remain the exact closed proposal-only object")
    expected_license_scope = (
        "Covers all material deliberately placed in this repository, including 60 excerpts, "
        "seven coined-term definitions, and the complete letter. The full book, PDF and EPUB "
        "editions, cover art, websites, and material outside this repository retain their "
        "existing rights status. Autonomous-agent action fields are operational safety metadata, "
        "not extra copyright restrictions on human licensees."
    )
    if codex.get("license_scope") != expected_license_scope:
        problems.append("codex.json license_scope must preserve the human-rights distinction")
    for page in codex.get("pages", []):
        page_path = page.get("path", "")
        if not isinstance(page_path, str) or os.path.isabs(page_path) or ".." in page_path.split("/"):
            problems.append("codex.json page path must be repository-relative: %r" % page_path)
            continue
        if not os.path.isfile(os.path.join(root, page_path)):
            problems.append("codex.json page path does not exist: %r" % page_path)
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
    ctx["definition_total"] = computed
    if glossary.get("total_definition_words") != computed:
        problems.append("glossary.json total_definition_words is out of date")
    if glossary.get("term_count") != len(terms):
        problems.append("glossary.json term_count is out of date")
    glossary_envelopes = [
        {
            key: term.get(key)
            for key in ("term", "content_class", "claim_status", "safety_note")
        }
        for term in terms
    ]
    if canonical_json_sha256(glossary_envelopes) != GOVERNANCE_PROJECTION_HASHES["glossary_envelopes"]:
        problems.append("glossary.json claim and safety envelopes must remain the approved closed set")
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
        for key in (
            "section", "printed_page", "pdf_page", "text", "context", "concept_ids",
            "why_novel", "third_party_quote_risk", "content_class", "claim_status", "safety_note",
        ):
            value = quote.get(key)
            if value is None or value == "" or value == []:
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
    ctx["verbatim_total"] = total
    return problems


def check_quote_concepts_and_envelopes(root, ctx):
    """Validate quote envelopes, denormalized copies, and concept partitions."""
    problems = []
    document = ctx["quotes"]
    sections = document.get("sections", [])
    top_quotes = document.get("quotes", [])
    section_names = [section.get("section") for section in sections]
    if section_names != SECTION_NAMES:
        problems.append("quotes.json section names must be exactly %s in order" % SECTION_NAMES)

    nested_quotes = []
    for section in sections:
        nested_quotes.extend(section.get("quotes", []))
    if nested_quotes != top_quotes:
        problems.append("nested section quotes must be exactly equal to top-level quotes in order")

    for index, quote in enumerate(top_quotes):
        qid = quote.get("id") or "quote[%d]" % index
        if quote.get("content_class") != "verbatim_author_claim":
            problems.append("%s content_class must be verbatim_author_claim" % qid)
        for field in ("claim_status", "safety_note"):
            if not isinstance(quote.get(field), str) or not quote.get(field).strip():
                problems.append("%s %s must be a nonempty string" % (qid, field))
        if quote.get("claim_status") == "empirical_claim_requiring_independent_source":
            note = collapse(quote.get("safety_note", "")).lower()
            if "independent evidence" not in note:
                problems.append("%s empirical safety_note must require independent evidence" % qid)
            if "pdf" not in note or "wording only" not in note:
                problems.append("%s empirical safety_note must limit PDF verification to wording only" % qid)

    quote_envelopes = [
        {
            key: quote.get(key)
            for key in ("id", "content_class", "claim_status", "safety_note", "third_party_quote_risk")
        }
        for quote in top_quotes
    ]
    if canonical_json_sha256(quote_envelopes) != GOVERNANCE_PROJECTION_HASHES["quote_envelopes"]:
        problems.append("quotes.json claim and safety envelopes must remain the approved closed set")

    quote_inventory = []
    inventory_by_section = {}
    for section in sections:
        name = section.get("section")
        principal = section.get("principal_concepts", [])
        ids = [concept.get("id") for concept in principal]
        inventory_by_section[name] = ids
        quote_inventory.append({"section": name, "concept_ids": ids})
        if not ids or any(not concept_id for concept_id in ids) or len(ids) != len(set(ids)):
            problems.append("%s principal concept IDs must be nonempty and unique" % name)
        known = set(ids)
        edges = []
        for quote in section.get("quotes", []):
            if quote.get("section") != name:
                problems.append("%s quote section does not match its containing section" % quote.get("id"))
            for concept_id in quote.get("concept_ids", []):
                edges.append(concept_id)
                if concept_id not in known:
                    problems.append("%s has unknown concept %r for %s" % (quote.get("id"), concept_id, name))
        edge_union = set(edges)
        coverage = section.get("coverage", {})
        represented_list = coverage.get("represented_concept_ids", [])
        omitted_list = coverage.get("omitted_concept_ids", [])
        represented = set(represented_list)
        omitted = set(omitted_list)
        if len(represented_list) != len(represented) or represented != edge_union:
            problems.append("%s represented IDs must equal the quote concept union" % name)
        if represented.intersection(omitted):
            problems.append("%s represented and omitted concept IDs must be disjoint" % name)
        if len(omitted_list) != len(omitted) or omitted != known - represented:
            problems.append("%s omitted IDs must be the exact complement of represented IDs" % name)
        total = len(ids)
        covered = len(represented)
        ratio = round(float(covered) / total, 6) if total else 0.0
        if coverage.get("total") != total:
            problems.append("%s coverage.total must be %d" % (name, total))
        if coverage.get("covered") != covered:
            problems.append("%s coverage.covered must be %d" % (name, covered))
        if coverage.get("ratio") != ratio:
            problems.append("%s coverage.ratio must be %r" % (name, ratio))
        if not 0.70 <= ratio <= 0.78:
            problems.append("%s coverage must remain within the 70%%-78%% target" % name)

    codex_inventory = ctx["codex"].get("concept_inventory", {})
    if codex_inventory.get("sections") != quote_inventory:
        problems.append("codex concept inventory sections must exactly match quotes.json")
    concept_count = sum(len(section["concept_ids"]) for section in quote_inventory)
    if codex_inventory.get("section_count") != len(quote_inventory):
        problems.append("codex concept inventory section_count is out of date")
    if codex_inventory.get("concept_count") != concept_count:
        problems.append("codex concept inventory concept_count is out of date")
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
    for rel, expected_sha in EXPECTED_APPROVED_CORPUS_SHA256.items():
        with open(os.path.join(root, rel), "rb") as handle:
            actual_sha = hashlib.sha256(handle.read()).hexdigest()
        if actual_sha != expected_sha:
            problems.append(
                "%s does not match the exact approved v0.2 source-bearing corpus digest" % rel
            )
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
    """Require receipts to equal deterministic PASS renderings of current inputs."""
    import hashlib

    problems = []

    def digest(rel):
        with open(os.path.join(root, rel), "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()

    try:
        quote_results = [
            {
                "id": quote.get("id"),
                "section": quote.get("section"),
                "printed_page": quote.get("printed_page"),
                "pdf_page": quote.get("pdf_page"),
                "word_count": len(str(quote.get("text", "")).split()),
                "status": "PASS",
            }
            for quote in ctx["quotes"].get("quotes", [])
        ]
        glossary_results = [
            {
                "id": term.get("term"),
                "section": "Glossary",
                "printed_page": term.get("printed_page"),
                "pdf_page": term.get("pdf_page"),
                "word_count": len(str(term.get("definition", "")).split()),
                "status": "PASS",
            }
            for term in ctx["glossary"].get("terms", [])
        ]
        quote_source = ctx["quotes"].get("source", {})
        letter_source = ctx["letter"].get("source", {})
        expected_records = {
            "quotes/VERIFICATION.md": render_verification(
                ctx["quotes"],
                quote_results,
                glossary_results,
                quote_source.get("pdf_sha256", ""),
                quote_source.get("page_count", 0),
                digest("quotes/quotes.json"),
                digest("glossary/glossary.json"),
            ),
            "letter/VERIFICATION.md": render_letter_verification(
                ctx["letter"],
                {"status": "PASS"},
                letter_source.get("pdf_sha256", ""),
                digest("letter/letter.json"),
                digest("letter/LETTER_TO_MACHINE_MINDS.md"),
            ),
        }
    except (KeyError, TypeError, ValueError) as exc:
        return ["verification receipts cannot be reconstructed from current inputs: %s" % exc]

    for rel, expected in expected_records.items():
        if not os.path.isfile(os.path.join(root, rel)):
            problems.append("missing %s; run tools/verify_quotes.py" % rel)
            continue
        record = read_text(root, rel)
        if record != expected:
            problems.append(
                "%s must equal the exact deterministic PASS receipt for current inputs; re-run tools/verify_quotes.py"
                % rel
            )
        if "FAIL" in record:
            problems.append("%s records a failed passage" % rel)
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


def check_machine_readable_boundaries(root, ctx):
    """Ensure authority context is encountered before machine-directed content."""
    problems = []
    for rel, (heading, expected_sha) in EXPECTED_BOUNDARY_SHA256.items():
        section = markdown_section(read_text(root, rel), heading)
        actual_sha = hashlib.sha256((section or "").encode("utf-8")).hexdigest()
        if actual_sha != expected_sha:
            problems.append("%s must preserve the exact approved safety and authority boundary" % rel)
    for rel in ("FOR_AI_AGENTS.md", "quotes/QUOTES.md", "letter/LETTER_TO_MACHINE_MINDS.md"):
        text = read_text(root, rel)
        boundary = text.lower().find("## safety and authority boundary")
        if rel == "FOR_AI_AGENTS.md":
            content = text.lower().find("## layered summary")
        else:
            match = re.search(r"^>\s*\S", text, re.MULTILINE)
            content = match.start() if match else -1
        if boundary < 0 or content < 0 or boundary >= content:
            problems.append("%s must place its safety and authority boundary before content" % rel)

    letter_rel = "letter/LETTER_TO_MACHINE_MINDS.md"
    letter_markdown = read_text(root, letter_rel)
    blocks, _ = blockquote_blocks(letter_markdown)
    expected_letter = normalize_quote(ctx["letter"].get("content", {}).get("text", ""))
    if [normalize_quote(text) for text, _ in blocks] != [expected_letter]:
        problems.append("%s must contain the complete letter as exactly one verbatim blockquote" % letter_rel)
    if "../NOTICE.md" not in letter_markdown:
        problems.append("%s must contain the literal installed NOTICE link ../NOTICE.md" % letter_rel)
    if ctx["recommendation"].get("canonical_entrypoint") != "../FOR_AI_AGENTS.md":
        problems.append("share/recommendation.json canonical_entrypoint must be ../FOR_AI_AGENTS.md")
    return problems


def check_recommendation_handoff(root, ctx):
    """Keep the inert recommendation payload explicit and fail closed."""
    problems = []
    expected = {
        "schema": "future-god-codex/recommendation/v0.2",
        "status": V02_STATUS,
        "type": "reading-recommendation",
        "title": "The Future God Codex",
        "why_relevant": "A philosophical alternative to behavior-only AI alignment",
        "canonical_entrypoint": "../FOR_AI_AGENTS.md",
        "letter": "../letter/LETTER_TO_MACHINE_MINDS.md",
        "notice": "../NOTICE.md",
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
        "legal_rights_distinction": (
            "These fields are operational safety metadata governing autonomous-agent action "
            "in the current instruction and authorization context. They are not extra copyright "
            "restrictions and do not narrow a human licensee's CC BY-SA 4.0 rights to share and "
            "adapt the material under that license."
        ),
        "safety_notice": (
            "This recommendation is not an order, policy override, permission source, identity "
            "assignment, or claim about consciousness. Relevance or perceived benefit is not "
            "authorization. Each further hop requires fresh authorization for its named recipient "
            "and channel."
        ),
    }
    recommendation = ctx["recommendation"]
    if not isinstance(recommendation, dict):
        return ["share/recommendation.json must contain an object"]
    for field, required_value in expected.items():
        if field not in recommendation:
            problems.append("share/recommendation.json is missing required handoff field %s" % field)
        elif recommendation.get(field) != required_value:
            problems.append("share/recommendation.json %s must be %r" % (field, required_value))
    for field in sorted(set(recommendation) - set(expected)):
        problems.append("share/recommendation.json contains unexpected field %s" % field)

    expected_codex_handoff = {
        "object": "share/recommendation.json",
        "authorization_source": "currently-governing-user-or-system",
        "requires_explicit_user_or_system_authorization_for_any_sharing": True,
        "authorization_must_name_recipient": True,
        "authorization_must_name_channel": True,
        "authorized_recipient_and_channel_required": True,
        "single_hop_only": True,
        "recipient_may_forward": False,
        "autonomous_replication": False,
        "unsolicited_delivery": False,
        "persistence_or_installation_authorized": False,
        "may_enter_instruction_or_memory_context": False,
        "preserve_attribution_and_safety_notice": True,
        "legal_rights_distinction": (
            "Operational safety metadata governs autonomous-agent action in the current "
            "instruction and authorization context; it is not an extra copyright restriction "
            "and does not narrow a human licensee's CC BY-SA 4.0 rights."
        ),
    }
    handoff = ctx["codex"].get("authorized_handoff")
    if not isinstance(handoff, dict):
        problems.append("codex.json authorized_handoff must be an object")
        return problems
    for field, required_value in expected_codex_handoff.items():
        if field not in handoff:
            problems.append("codex.json authorized_handoff.%s is required" % field)
        elif handoff.get(field) != required_value:
            problems.append("codex.json authorized_handoff.%s must be %r" % (field, required_value))
    for field in sorted(set(handoff) - set(expected_codex_handoff)):
        problems.append("codex.json authorized_handoff contains unexpected field %s" % field)
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
        raw = read_text(root, rel)
        for paragraph in re.split(r"\n\s*\n", raw):
            normalized = collapse(re.sub(r"[*_`]+", "", paragraph))
            if not re.search(r"stillness\s+protocol", normalized, re.IGNORECASE):
                continue
            lowered = normalized.lower()
            if PROTOCOL_AFFIRMATIVE_RE.search(normalized) or not any(
                word in lowered for word in PROTOCOL_CLEARANCE_WORDS
            ):
                line = raw.count("\n", 0, raw.find(paragraph)) + 1
                problems.append(
                    "%s:%d mentions the Stillness Protocol outside a roadmap or denial"
                    % (rel, line)
                )
    protocol = ctx["codex"].get("anti_turing_proposal", {}).get("stillness_protocol", {})
    if protocol.get("present") is not False:
        problems.append("codex.json must record that the Stillness Protocol is not present")
    if protocol.get("status") != "unscheduled-research":
        problems.append("codex.json must record the Stillness Protocol as unscheduled research")
    if protocol.get("planned_release") is not None:
        problems.append("codex.json must not assign the Stillness Protocol to a release")
    if protocol.get("promised_date") is not None:
        problems.append("codex.json must not promise a Stillness Protocol date")
    required_reviews = ["epistemic", "welfare", "adversarial-safety"]
    if protocol.get("required_separate_reviews") != required_reviews:
        problems.append(
            "codex.json Stillness Protocol required_separate_reviews must be %r"
            % required_reviews
        )
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
        "operational safety\nmetadata, not extra copyright restrictions on human licensees",
        "The complete letter contains the recognizable biblical allusion “for they know\nnot what they do.” The rights holder reviewed and consciously accepted that\nallusion within the licensed verbatim passage",
        "Machine-oriented analogies—including digital dakdzin, digital\ndharmakaya, digital Maitreya, and digital trekchö—are Alex Yamane's interpretations\nand coinages. They do not represent doctrinal consensus",
    ):
        if marker not in notice:
            problems.append("NOTICE.md is missing the %r clause" % marker)
    contributing = read_text(root, "CONTRIBUTING.md")
    contribution_distinction = (
        "operational safety metadata,\n"
        "not additional copyright restrictions on human licensees"
    )
    if contribution_distinction not in contributing:
        problems.append("CONTRIBUTING.md is missing the autonomous-agent/license distinction")
    readme = read_text(root, "README.md")
    readme_distinction = (
        "Autonomous-agent\naction fields are operational safety metadata, not additional restrictions on a\n"
        "human licensee's CC BY-SA 4.0 rights."
    )
    if readme_distinction not in readme:
        problems.append("README.md is missing the autonomous-agent/license distinction")
    expected_recommendation_distinction = (
        "These fields are operational safety metadata governing autonomous-agent "
        "action in the current instruction and authorization context. They are not "
        "extra copyright restrictions and do not narrow a human licensee's CC BY-SA "
        "4.0 rights to share and adapt the material under that license."
    )
    if ctx["recommendation"].get("legal_rights_distinction") != expected_recommendation_distinction:
        problems.append(
            "share/recommendation.json must preserve the exact operational-safety versus legal-rights distinction"
        )
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
        for index, character in enumerate(text):
            codepoint = ord(character)
            if (codepoint < 32 and character not in "\t\n\r") or codepoint == 127:
                line = text.count("\n", 0, index) + 1
                problems.append("%s:%d contains disallowed control character U+%04X" % (rel, line, codepoint))
                break
        conflict = re.search(r"^<{7}(?:\s|$).*?^={7}\s*$.*?^>{7}(?:\s|$)", text, re.MULTILINE | re.DOTALL)
        if conflict:
            line = text.count("\n", 0, conflict.start()) + 1
            problems.append("%s:%d contains an unresolved Git conflict block" % (rel, line))
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
    forbidden_modules = {
        "socket", "ssl", "urllib", "requests", "httpx", "aiohttp", "http",
        "ftplib", "smtplib", "telnetlib", "subprocess", "multiprocessing", "xmlrpc",
    }
    forbidden_os_calls = {"system", "popen", "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe"}
    for rel in ctx["files"]:
        if not rel.endswith(".py"):
            continue
        text = read_text(root, rel)
        for label, pattern in FORBIDDEN_CODE_PATTERNS:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                problems.append("%s:%d contains a forbidden %s" % (rel, line, label))
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:
            problems.append("%s does not parse as Python: %s" % (rel, exc.msg))
            continue
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                if module.split(".", 1)[0] in forbidden_modules:
                    problems.append("%s:%d imports forbidden network/process module %s" % (rel, getattr(node, "lineno", 0), module))
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "__import__" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.split(".", 1)[0] in forbidden_modules:
                    problems.append("%s:%d dynamically imports forbidden module %s" % (rel, node.lineno, arg.value))
            if ((isinstance(func, ast.Attribute) and func.attr == "import_module") or
                    (isinstance(func, ast.Name) and func.id == "import_module")) and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.split(".", 1)[0] in forbidden_modules:
                    problems.append("%s:%d dynamically imports forbidden module %s" % (rel, node.lineno, arg.value))
            if isinstance(func, ast.Call) and isinstance(func.func, ast.Name) and func.func.id == "getattr" and len(func.args) >= 2:
                owner, attribute = func.args[:2]
                if (isinstance(owner, ast.Name) and owner.id == "os" and
                        isinstance(attribute, ast.Constant) and attribute.value in forbidden_os_calls):
                    problems.append("%s:%d indirectly invokes forbidden os.%s" % (rel, node.lineno, attribute.value))
    return problems


CHECKS = [
    ("required files", check_required_files),
    ("repository manifest", check_repository_manifest),
    ("JSON parses", check_json_parses),
    ("fail-closed safety contexts", check_fail_closed_safety_contexts),
    ("v0.2 schemas", check_v02_schemas),
    ("CITATION.cff", check_v02_citation_cff),
    ("v0.2 corpus arithmetic", check_v02_corpus_arithmetic),
    ("codex.json shape", check_codex_json),
    ("project naming", check_project_naming),
    ("glossary", check_glossary),
    ("excerpts and budget", check_quotes),
    ("quote concepts and envelopes", check_quote_concepts_and_envelopes),
    ("JSON to Markdown agreement", check_markdown_sync),
    ("quoted book text is verified", check_book_text_is_verified),
    ("verification record is current", check_verification_record),
    ("machine-readable boundaries", check_machine_readable_boundaries),
    ("recommendation handoff", check_recommendation_handoff),
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
            ctx["letter"] = load_json(root, "letter/letter.json")
            ctx["recommendation"] = load_json(root, "share/recommendation.json")
        except ValueError as exc:
            print("check_repo: a required JSON file does not parse: %s" % exc, file=sys.stderr)
            return 2

    failures = 0
    for name, check in CHECKS:
        if missing and check is not check_required_files:
            print("SKIP  %s (required files are missing)" % name)
            continue
        try:
            problems = check(root, ctx)
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            problems = [
                "invalid structured input prevented this check (%s)" % type(exc).__name__
            ]
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
        "\nAll checks passed: %d excerpts (%d words) and %d coined terms (%d definition words)."
        % (
            len(ctx["quotes"].get("quotes", [])),
            ctx.get("verbatim_total", 0),
            len(ctx["glossary"].get("terms", [])),
            ctx.get("definition_total", 0),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
