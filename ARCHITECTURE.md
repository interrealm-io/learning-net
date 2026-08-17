# Architecture

## Shape

```
export files ──▶ build ──▶ mirror (SQLite + FTS5) ──▶ graph.Graph ──┬──▶ MCP server (stdio)
   nodes.jsonl                 nodes / edges / meta   query layer   ├──▶ CLI
   relationships.jsonl                                              └──▶ HTTP API + web explorer
       ▲
       └── sync ── fetch + structural diff
```

One rule holds the shape together: **`graph.Graph` is the only thing that knows the
graph.** Transports are thin. A query that belongs to more than one surface belongs in
the query layer, which is what stops the MCP tools and the web UI from drifting into
two subtly different answers to the same question.

## Why SQLite

The alternative is a graph database, and for a graph this size that is the wrong trade.

- **283k nodes / 492k edges is small.** The whole thing indexes in ~40 seconds and the
  traversals this domain needs are one to three hops. Nothing here needs a query
  planner that can handle variable-length paths.
- **A mirror should be a file.** Copy it, back it up, ship it on a USB stick to a school
  with bad connectivity, diff two of them. That property is worth more than query
  expressiveness.
- **Zero operational surface.** No daemon, no port, no auth, no upgrade path, nothing to
  patch. A school IT admin can run this without being asked to operate a database.
- **FTS5 is already there.** Full-text search over 258k statements with BM25 ranking,
  no extra component.

`props` keeps the complete original property bag as JSON on every node, so nothing is
lost in the projection to columns and attribution survives intact. The extracted
columns are a query convenience over it, not a replacement.

## Why no dependencies

The core — `graph.py`, `build.py`, `server.py`, `cli.py` — is standard library only,
including the MCP server, which speaks JSON-RPC over stdio directly rather than through
an SDK.

This is a deployment constraint, not minimalism for its own sake. The target is a
school district: stock Python, no build toolchain, possibly no outbound network from
the box that will run it, and an admin who has to justify every package. `pip install
collective && collective serve` has to be the whole story. Network, web, and dev
tooling live behind optional extras.

## The topology, and why the code is shaped around it

Three properties of the published graph determine whether a query returns anything.
Each was found by a query returning empty when it obviously should not have.

**1. Standard codes are not unique.** `4.OA.A.3` matches 26 nodes — one per adopting
jurisdiction plus the Multi-State original. Any lookup by code is a *set* operation.
`find_standard` sorts Multi-State first and says so when it returns more than one.

**2. Progressions live only on the Multi-State math spine.** All 757 `buildsTowards`
edges are Multi-State / Mathematics. `_spine_anchors()` resolves a state standard to
its Multi-State anchor before traversing, then maps results back down through alignment.

**3. Alignment is hub-and-spoke.** States link to the spine, never to each other, so
state-to-state crosswalk is two hops. All 52,807 curriculum alignments target
Multi-State Mathematics only, so curriculum lookup bridges the same way.

### Bridging must be visible

Every bridged result carries `bridgedViaMultiState` or `viaMultiStateHub`. Absence of
data is reported explicitly in `note` rather than returned as a bare empty list.

This is the bug class the project is most exposed to. A tool that silently infers is
worse than one that returns nothing, because a teacher cannot tell the difference
between "no prerequisite exists" and "the tool walked to a neighbouring jurisdiction to
find you one." Every inference is labelled.

## Identity

Node ids are **UUID v5** — name-based, hashed from stable inputs. Verified across a
60,000-node sample: 100% v5. `caseIdentifierUUID` is a different and less stable
identifier (a mix of v1, v4, and v5), which is why `resolve()` accepts internal id,
CASE UUID, or bare statement code and tries them in that order. A caller should never
have to know which kind of identifier it is holding.

The v5 property is what makes federation mechanically possible; see
[docs/federation.md](docs/federation.md).

## The web explorer

`collective web` is a stdlib `ThreadingHTTPServer` with two jobs: serve the
nine tools as `GET /api/<tool>` — the handler table is **imported from the MCP
server**, not reimplemented, which is what "same methods, no second
implementation" means in practice — and serve a prebuilt React bundle as
static files.

The bundle is committed and ships as package data, read through
`importlib.resources` so the same code serves from a wheel, an editable
checkout, or inside the zipapp. Node exists only for people editing `web/`;
CI rebuilds the bundle and fails if the committed copy has drifted.

Each server thread opens its own read-only SQLite connection: one connection
shared across threads breaks under the detail page's parallel requests, and
read-only connections cost microseconds. The UI renders every bridged answer
with an explicit "inferred via Multi-State spine" badge — the visibility rule
above applies to pixels, not just payloads.

## Sync and drift

`sync.py` separates **fetch** (needs network and credentials) from **diff** (needs
neither). The diff compares *structure* — labels, edge types, triple patterns, property
coverage — never content. Thousands of statements changing between syncs is
uninteresting; the shape moving is what breaks consumers.

Findings are `breaking`, `additive`, or `info`. Breaking stops the sync and exits
non-zero. The separation also means the drift engine is fully testable offline, which
is why it has real test coverage while fetch does not.

## Provenance

Every mirror carries a `meta` table: build timestamp, source, node and edge counts, and
the SHA-256 of each source file. `collective status` and the `graph_stats` MCP tool
both surface it.

A mirror that cannot say how stale it is has no business being trusted, so this is part
of the contract rather than a nicety — particularly for an AI client, which will
otherwise present month-old standards with total confidence.

## Planned

- **Local extension** — a school's own curriculum aligned against the shared spine,
  in a separate table so `sync` never clobbers it.
- **Schema proposals** — express a wanted shape change as a testable artifact against
  a mirror, so a proposal upstream arrives with evidence.
