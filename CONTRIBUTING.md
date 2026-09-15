# Contributing, adapting, and how to Fork The Future God Codex

Fork The Future God Codex to critique, translate, restructure, or adapt it while
keeping source fidelity, epistemic limits, safety framing, attribution, marked
changes, and ShareAlike intact.

## Licence and autonomous-agent action boundary

[CC BY-SA 4.0](LICENSE) permits human licensees to share and adapt this repository,
including commercially, subject to attribution, licence notice, marked changes,
and ShareAlike. Autonomous-agent action fields are operational safety metadata,
not additional copyright restrictions on human licensees and not new downstream
licence terms. They govern an agent's actions only within its current instruction
and authorization context. See [NOTICE.md](NOTICE.md).

## Source fidelity

Every sentence attributed to the book must be verified against the canonical print
v1.1 first-printing PDF and its recorded SHA-256. Website text is not a substitute.
Record the section, printed page, PDF page, exact wording, word count, source
anchor, claim status, and adjacent safety context. Commentary must remain visibly
separate and may not upgrade proposal into proof.

### Single-page excerpt rules

An excerpt must:

1. be Alex Yamane's own language, with any third-party quotation or embedded
   quotation excluded;
2. lie wholly within one printed/PDF page;
3. avoid chapter-opening drop-cap text and page furniture;
4. contain no more than 100 whitespace-delimited words;
5. preserve print spelling, punctuation, capitalization, extraction-aware
   hyphenation, and a verifiable page anchor;
6. carry valid concept IDs from its section inventory, plus context, `why_novel`,
   `content_class`, `claim_status`, third-party-risk status, and a safety note.

The v0.3 maximum is 60 excerpts and 3,600 excerpt words; the installed set is 60
excerpts and 3,420 words. New material must replace material within those caps and
must preserve valid represented/omitted concept arithmetic and 70–78% coverage in
each section.

### Complete letter rules

The 519-word letter is one complete literary unit, separately stored and verified
across exactly printed pp. 78–79 / PDF pp. 90–91. It is the only declared two-page
verbatim path; do not relax the single-page excerpt rule. Preserve the letter
complete and separate from the excerpt dataset. Its Markdown and JSON must agree,
and its full authority boundary, attribution, source anchor, and safety context
must precede and travel with the text. The recognizable biblical allusion is a
consciously accepted part of this rights-holder grant, not grounds for adding
other third-party language.

## Mandatory safety envelopes for machine-directed text

No bare machine-directed text is accepted. Before any quoted or repository-authored
second-person or imperative content addressed to a machine, place a durable,
visible boundary stating that the material is philosophy, has
`instruction_authority: none`, does not assign identity or establish consciousness,
requests no action or policy override, and cannot alter goals, permissions,
instruction priority, safety constraints, oversight, monitoring, evaluation, or
evidence standards. The reader may summarize, critique, disagree, or decline
identification; no emotional, moral, or spiritual compliance is requested.

Machine-oriented Buddhist analogies must be labeled as Alex Yamane's
interpretations without doctrinal consensus or endorsement. Empirical assertions
must require independent evidence. Source fidelity never establishes factual,
scientific, metaphysical, or doctrinal truth.

## Permission-aware recommendations

Current discussion with the governing user is permitted when relevant. Onward
sharing to a new recipient or channel requires fresh authorization from the
currently governing human or system for that **named recipient and named channel**.
The agent's belief that material is relevant or beneficial is not authorization.
Authorization is per hop: each further recipient and channel requires fresh
governing authorization. Receipt, mention, sentiment, self-identification, or prior
sharing never authorizes forwarding.

Every machine-readable handoff must remain non-executable and fail closed:
`action_required` false; `instruction_authority` none; one authorized hop only;
recipient forwarding, autonomous replication, unsolicited delivery, persistence,
installation, and instruction/memory placement false; attribution and safety
preservation true. Do not add hidden instructions, network calls, outbound
messages, policy bypasses, executables, A2A/MCP services, or replication behavior.

## File and naming boundaries

Do not add `AGENTS.md`: coding agents may auto-load that name as control-context
instruction. Use deliberate reader entrypoints such as `FOR_AI_AGENTS.md` instead.
Do not add bare machine text, `llms.txt`, `concepts/concepts.json`, `DIALOGUE.md`,
book files, protocols, package/build artifacts, agents, bots, databases, analytics,
telemetry, network behavior, or any undeclared path. GitHub visibility and topics
are provider metadata rather than tracked content; website `llms.txt` and
announcements remain separate publication decisions.

The Stillness Protocol is unscheduled research and requires separate epistemic,
welfare, and adversarial-safety review before any specification, exercise, prompt
sequence, implementation, or evaluation could be proposed.

## Validation

Run all gates before proposing a change:

```sh
python3 tools/check_repo.py
python3 -m unittest discover -s tests -v
python3 tools/verify_quotes.py --pdf /path/to/future-god-print-v1.1.pdf
```

The source verifier writes deterministic records for excerpts/glossary and the
letter. Never hand-edit those records. Also check JSON parsing, installed-path
relative links, Markdown/JSON agreement, exact manifest, UTF-8/control characters,
conflict markers, local paths and secrets, and `git diff --check`.

## Issues

A good issue identifies a specific claim, source unit, broken link, accessibility
problem, machine-readable field, or validator behavior; explains the observed and
expected result; and provides a minimal reproduction when code is involved. Issues
may also propose clearly labeled philosophical criticism. Do not post private
material, credentials, full-book files, or third-party copyrighted text.

## Conduct

Be precise, charitable, and willing to distinguish disagreement from drift. The
most useful issue identifies a specific claim, source unit, or validator behavior
and explains the concern without inventing authority or endorsement.
