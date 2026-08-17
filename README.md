# Collective

**A self-hostable mirror, MCP server, and explorer for the Learning Commons Knowledge Graph.**
An independent, open-source **extension to the [Learning Commons Platform](https://www.learningcommons.org)**.

Learning Commons has aggregated something genuinely hard to assemble: K-12 academic
standards across 52 US jurisdictions, the granular learning components beneath them,
the alignments between them, and curriculum mapped onto them — 283,381 nodes and
492,169 edges, published under CC BY-4.0.

Collective makes that graph something a school can **run**. Sync it, host it, query
it, explore it, extend it. No network round-trip per lookup, no rate limit, no single
point of failure, and no requirement that anyone else's server be up for a classroom
to work.

Commons is the collection. Collective is the distribution.

> **Status: alpha.** Upstream is in private beta and explicitly evolving with breaking
> changes. Sync reports schema drift rather than absorbing it — see
> [Drift is a feature](#drift-is-a-feature).

---

## Why this exists

Query the hosted Knowledge Graph for the prerequisites of California's `4.OA.A.3` and
you get nothing back. Not an error — an empty list. The standard is real, the
progression data is real, and the answer is still empty.

The reason is structural. Progression edges are authored **only** on the Multi-State
(Common Core) spine — 757 of them, all mathematics. No state standard carries one
directly. To answer the question you have to know to hop out to the aligned
Multi-State standard, walk the progression there, and map the results back down.

That is one of three topology facts that decide whether a query returns anything:

1. **Standard codes are not unique.** `4.OA.A.3` matches 26 nodes — one per adopting
   jurisdiction, plus the Multi-State original.
2. **Progressions live only on the Multi-State math spine.** No state standard has one
   directly; no ELA, Science, or Social Studies standard has one at all.
3. **Alignment is hub-and-spoke.** States link to Multi-State, never to each other, so
   a California → Texas crosswalk is two hops. All 52,807 curriculum alignments
   likewise point only at Multi-State Mathematics.

None of this is documented, and all of it is discoverable only by getting an empty
result and not believing it. Collective encodes all three, bridges automatically,
and **tells you when it bridged** — every result that crossed the spine says
`bridgedViaMultiState` or `viaMultiStateHub`, so you can always separate what the data
says from what the tool inferred.

## What you get

| Feature | Hosted KG | Collective |
| :--- | :---: | :---: |
| Resolve a standard code | Yes | **Yes** |
| Learning components | Yes | **Yes** |
| Progressions | Yes, one hop | **Yes, auto-bridged** |
| Full-text search across all statements | — | **Yes** |
| Cross-jurisdiction crosswalk | — | **Yes, auto two-hop** |
| Framework context (ancestors, children) | — | **Yes** |
| Aligned curriculum | — | **Yes, auto-bridged** |
| Raw node access | — | **Yes** |
| Browse it in a web UI | — | **Yes**, `collective web` |
| Works offline | — | **Yes** |
| Runs on your hardware | — | **Yes** |
| Says which upstream release it is | — | **Yes** |

By exposing the graph as a local MCP server, any LLM agent or developer tool can
query, navigate, and reason over US K-12 academic standards with zero API
overhead — no key, no rate limit, no network round-trip per lookup.

## Quick start

```bash
git clone https://github.com/interwax/collective && cd collective
python3 demo.py              # Windows: py demo.py
```

That's it. The script creates a private `.venv`, installs the package,
downloads ~900MB of exports, builds the mirror, and opens the explorer in a
browser tab. Every step is skipped once done, so the same command is also the
fastest relaunch. Stock Python 3.11+ is the only prerequisite, on every OS.

Prefer the CLI on your PATH? Install it directly instead:

```bash
uv tool install .            # or: pipx install .
collective init              # downloads ~900MB and builds the mirror
collective web --open        # the explorer
```

No `uv` or `pipx`? A plain venv works too — `python3 -m venv .venv &&
.venv/bin/pip install -e .` — or skip installation entirely with the
[single-file build](#no-pip-one-file) below. (A bare `pip install` outside a
venv is refused on modern Homebrew and Debian Python — that is
[PEP 668](https://peps.python.org/pep-0668/), not a bug in this project.)

That is the whole setup. Upstream publishes versioned exports on a public CDN,
so there is no API key, no account, and no request form:

```
https://cdn.learningcommons.org/knowledge-graph/v1.12.0/exports/nodes.jsonl
https://cdn.learningcommons.org/knowledge-graph/v1.12.0/exports/relationships.jsonl
```

Then:

```bash
collective status                                    # what is in it, which upstream release
collective query crosswalk standard=4.OA.A.3 toJurisdiction=Texas
collective update                                    # is there a newer release?
collective sync --version 1.13.0 --changelog cl.json # fetch, diff, report, rebuild
```

Already have the export files? `collective build <dir>` skips the download.

### No pip? One file.

The core is stdlib-only, so the whole tool also ships as a single-file
[zipapp](https://docs.python.org/3/library/zipapp.html). If `pip` is unavailable or
forbidden on your machine, download `collective.pyz` from the
[latest release](https://github.com/interwax/collective/releases/latest) and run it
with the Python you already have — nothing to install, nothing on PATH:

```bash
python3 collective.pyz init
python3 collective.pyz status --db data/kg.sqlite
```

Every command works the same way: wherever the docs say `collective`, say
`python3 collective.pyz`. To build it from a checkout, run `make pyz`.

Point any MCP client at it:

```json
{
  "mcpServers": {
    "collective": {
      "command": "collective",
      "args": ["serve", "--db", "/srv/collective/data/kg.sqlite"]
    }
  }
}
```

(With the zipapp, use `"command": "python3"` and put the `.pyz` path first in `args`.)

Or browse it. `collective web --open` serves a local explorer — full-text search,
standard detail with prerequisites and aligned curriculum, cross-state crosswalk,
and a status dashboard — over the **same nine queries** the MCP tools answer, so
the two surfaces cannot disagree. Every answer that crossed the Multi-State spine
wears a visible "inferred" badge in the UI, same as in the JSON. The UI is a
prebuilt bundle that ships inside the package: no Node, no build step, stdlib
Python serves it.

The core has **zero dependencies** — stdlib Python only, including the MCP server. A
school IT admin with a stock Python install can run the whole thing. Network access is
needed only to `sync`, and even that is optional if the export arrives another way.

## Drift is a feature

Upstream is in private beta and says so. A mirror that silently absorbs a schema change
is worse than no mirror: it will keep answering confidently from a shape that no longer
matches reality. Collective is designed to fail loudly instead — sync detects, diffs,
and reports schema drift rather than masking it.

So `collective sync` compares the **structure** of a new export against the live
mirror — labels, edge types, triple patterns, property coverage — and classifies what
moved:

```
  [breaking] edge-type-removed      buildsTowards (was 757 edges)
  [breaking] property-removed       StandardsFrameworkItem.statementCode (was on 73% of nodes)
  [additive] node-label-added       Competency (1,204 nodes)
  [info    ] volume-change          LearningComponent  8,686 → 12,431  (+43%)
```

Breaking findings stop the sync and exit non-zero. Use `--check` in CI to be told
before a classroom is.

That report is also the most useful thing this project can hand back upstream: it is a
changelog Learning Commons does not currently publish.

## Federation

Every node id in the published graph is a **UUID v5** — name-based, derived by hash
from stable inputs, never randomly assigned. Two independently built mirrors of the
same source produce byte-identical ids.

That is the whole basis for federation, and it is already true. A district can add its
own curriculum against the shared spine and the additions merge without an id
reconciliation layer. A schema-change proposal can reference nodes unambiguously across
instances. See [docs/federation.md](docs/federation.md).

## Licensing, in one paragraph

The **code** is Apache-2.0. The **data** is Learning Commons' work, published under
CC BY-4.0, and every node and edge carries its own `license` and a per-jurisdiction
`attributionStatement` naming the source department. Collective preserves both,
verbatim, and surfaces them in every export path. Redistribution with attribution is
what CC BY-4.0 grants; this project exercises exactly that and nothing more. See
[DATA-LICENSE.md](DATA-LICENSE.md).

Upstream publishes the exports on a public CDN with no credential and no gate, so
mirroring requires nothing beyond the license they already granted. Their authenticated
MCP API is a separate surface governed by whatever agreement you have with them —
Collective does not touch it.

## Governance

Collective is stewarded by the **InterRealm Foundation** as non-profit open
infrastructure for educational AI. It is not a commercial open-core product and there
is no paid tier. What is and is not in scope — and specifically what happens to a
school's own curriculum if they put it in a mirror — is written down in
[GOVERNANCE.md](GOVERNANCE.md) rather than left to trust.

Collective is authored and maintained by **Duncan Krebs**, Founder and Executive
Director of the InterRealm Foundation. Questions about scope, stewardship, or pilot
use: [hello@interrealm.org](mailto:hello@interrealm.org).

## Roadmap

- **PyPI release** — so `uv tool install collective` works without a checkout.
- **Local extension** — a school's own curriculum aligned against the shared
  spine, in a separate table so `sync` never clobbers it.
- **Federation tooling** — shared-spine merges across instances; the groundwork
  is in [docs/federation.md](docs/federation.md).

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — how the mirror is built and why it is shaped this way
- [docs/federation.md](docs/federation.md) — the UUID v5 argument, and what federation would require
- [DATA-LICENSE.md](DATA-LICENSE.md) — attribution obligations, and how they are met
- [GOVERNANCE.md](GOVERNANCE.md) — stewardship, scope, and the open/commercial boundary
- [CONTRIBUTING.md](CONTRIBUTING.md)

## Acknowledgement

This project exists because Learning Commons did the hard part. Aggregating,
normalizing, and openly licensing the standards of 52 jurisdictions is years of
unglamorous work, and publishing it under CC BY-4.0 was a choice they did not have to
make. Collective is a distribution layer on top of that, built in the spirit the
license invites.

---

<div align="center">
  <sub>Built by Duncan &amp; Claude for the InterRealm Foundation. 🤍</sub>
</div>
