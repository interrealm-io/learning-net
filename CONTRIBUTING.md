# Contributing

## Setup

```bash
git clone https://github.com/interwax/collective
cd collective
make install                  # venv at .venv with dev extras
source .venv/bin/activate
pytest
```

Tests run against a small synthetic mirror built in a fixture — you do not need the
700 MB national graph to develop, and CI does not download it.

## The one rule

**Every claim about the graph's shape needs a test.**

This project exists because the upstream topology has properties that are invisible
until a query returns empty: codes are not unique, progressions live only on the
Multi-State math spine, alignment is hub-and-spoke. Each of those is encoded as a
bridging behaviour, and each bridging behaviour has a test that fails if it is dropped.

If you add a query that bridges, traverses, or infers, add the test that catches its
removal. If you find a new topology fact, document it in `graph.py`'s module docstring
and test it.

## Bridging must be visible

Any result that crossed the Multi-State spine to find its answer must say so in the
payload — `bridgedViaMultiState`, `viaMultiStateHub`, or an equivalent flag. A caller
must always be able to separate what the data states from what the tool inferred.
Silent inference is the bug class this project is most exposed to.

## Working on the web UI

The explorer's source lives in `web/` (Vite + React + TypeScript). The built
bundle is **committed** at `src/collective/static/` so runtime machines never
need Node — which means UI changes are a two-step:

```bash
make ui        # npm install + build into src/collective/static
git add web src/collective/static
```

CI rebuilds the bundle and fails the PR if the committed copy doesn't match
the source. `npm run dev` inside `web/` gives hot reload, proxying `/api` to a
`collective web` server on port 8788.

## No dependencies in the core

`graph.py`, `build.py`, `server.py`, `web.py`, and `cli.py` are stdlib-only and
stay that way.
A school IT admin with a stock Python install must be able to run the mirror and the
MCP server. Network, web, and dev tooling live behind optional extras.

## Style

`ruff` with the repo config. 100 columns. Comments explain *why* — the topology facts,
the licensing distinction, the reason a query bridges — not what the code does.
