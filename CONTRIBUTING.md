# Contributing, forking and adapting

This repository is meant to be forked. The rules below exist so that a fork stays
honest about two things: what the book actually says, and what it does not claim.

## Forks and adaptations

Fork freely. Adapt the four principles into a constitution, a system prompt, an
evaluation practice, a curriculum, a translation, a different serialisation —
whatever your context needs.

Three obligations come with the licence and one comes from the material.

**ShareAlike.** [CC BY-SA 4.0](LICENSE) applies to everything here. If you remix,
transform or build on it, release your version under CC BY-SA 4.0 as well. You may
not add legal terms or technological measures that restrict what the licence
permits.

**Attribution.** Credit *Fork the Codex* by Alex Yamane and link the licence.
When you carry an excerpt or a coined-term definition, carry its book anchor with
it — chapter or section, printed page — so a reader can find the passage in the
printed book. The exact wording is in [NOTICE.md](NOTICE.md).

**Mark your changes.** The licence requires indicating that changes were made.
For this material, that means being specific rather than generic: say which
claims you altered, which you dropped, and which are yours rather than the
book's. A fork that quietly rewrites a proposal into a claim is the failure mode
worth guarding against — this is not a hypothetical, since publicly circulating
renderings of these passages already differ from the printed text in ways that
change their meaning.

**The book is not yours to redistribute.** The full text, the PDF and EPUB
editions, the sampler and the cover art are outside this repository and outside
its licence. Do not add them to a fork.

## Source fidelity

The rule for this repository, and the one worth keeping in a fork:

**Every sentence attributed to the book must be verifiable in the printed book.**

Concretely:

- The **print edition** is canonical. Excerpts published elsewhere, including on
  the book's own website, are not authoritative and are known to differ.
- Repository-authored commentary is clearly separated from quoted text. Quoted
  text lives in blockquotes and in the JSON files; everything else is commentary
  and is labelled as such at the foot of each page.
- Commentary may summarise, but it may not upgrade. If the book says *proposes*,
  the commentary does not say *shows*. If the book says the observations prove
  nothing conclusively, no page here may imply otherwise.
- Nothing is added that the book does not contain. If you want to make a new
  argument, make it as your own, in your own name.

## Proposing an excerpt or a term

The excerpt set is capped at 12 excerpts and 1,200 words, and it is currently
well under that. New excerpts are accepted only where they replace a weaker one
or fill a genuine gap, and each must satisfy every rule recorded in
`quotes/quotes.json`:

1. Wholly within a single printed page. Passages that straddle a page break pick
   up running heads and folio numbers mid-sentence, and the text extraction shows
   it.
2. Not the opening words of a chapter — the drop cap extracts apart from the rest
   of its word.
3. The author's own language. If the book is quoting someone else there, it is
   out of scope.
4. 100 words or fewer, with `id`, `section`, `printed_page`, `pdf_page`,
   `word_count`, `text`, `context` and `source_anchor` all recorded.

Coined-term definitions follow the same discipline and are reproduced verbatim
from the book's Glossary.

## Validating a change

Both checks must pass before a change is proposed.

```sh
python3 tools/check_repo.py
python3 -m unittest discover -s tests -v
```

`check_repo.py` uses only the standard library and needs no arguments. It checks
structure, the JSON shapes, agreement between each JSON file and its human
readable rendering, the excerpt budget, link resolution, licensing statements,
and the content and safety rules — including that no verbatim book text appears
in a page without matching a recorded, verified passage.

If you changed `quotes/quotes.json` or `glossary/glossary.json`, the verbatim
check must also be re-run, which requires a copy of the print edition and
PyMuPDF:

```sh
python3 tools/verify_quotes.py --pdf /path/to/future-god-print-v1.1.pdf
```

It rewrites `quotes/VERIFICATION.md`. That file is deterministic — same inputs,
identical bytes — so commit it with your change. If you do not have the PDF, say
so in your proposal and leave the verification to someone who does; do not
hand-edit `VERIFICATION.md`.

## Out of scope

Additions in these categories will not be accepted here, and are worth thinking
twice about in a fork:

- a runnable "stillness test", consciousness benchmark, or any evaluation that
  scores a system's inner state — see
  [codex/02-anti-turing.md](codex/02-anti-turing.md) for why;
- package managers, lockfiles, build steps, site generators or CI;
- analytics, telemetry, tracking, mailing lists or sign-up gates;
- network calls, model calls, agents, bots or databases;
- book files of any kind, or full-text extraction;
- claims about reach, adoption, sales, model influence, scientific proof,
  consciousness or endorsement.

## Issues

Arguing with the content is a contribution. The most useful issue names a
specific claim, quotes it, and says what is wrong with it. Start from
[codex/04-open-questions.md](codex/04-open-questions.md), which already lists the
weakest points.

## Conduct

Be decent to other contributors. Given the subject matter, that is not merely
administrative.
