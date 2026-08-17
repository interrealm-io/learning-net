# Data license and attribution

Collective's **code** is Apache-2.0 (see [LICENSE](LICENSE)). This file is about the
**data**, which is not ours.

## What the data is

The Learning Commons Knowledge Graph, published by Learning Commons under
**Creative Commons Attribution 4.0 International (CC BY-4.0)**.

Every node and every edge in the graph carries two properties that Collective treats
as load-bearing and never strips:

- `license` — the CC BY-4.0 URI
- `attributionStatement` — the full attribution, naming Learning Commons and the
  originating jurisdiction's department of education

A representative one:

> Knowledge Graph is provided by Learning Commons under the CC BY-4.0 license.
> Tennessee Mathematics standards provided by Tennessee Department of Education
> available at https://www.tn.gov/...

Underlying standards remain the work of the issuing state departments of education,
and several sub-collections carry their own additional attribution — Achievement
Network (learning components), Illustrative Mathematics (curriculum), Carnegie
Foundation and ETS (durable skills), XQ Institute (competencies).

## How Collective meets the obligation

CC BY-4.0 permits redistribution and derivative works, including commercial use,
provided attribution is preserved. Concretely:

1. **Attribution is never dropped in the build.** `attributionStatement` and `license`
   survive into the mirror inside each node's full property bag, and `get_node` returns
   them verbatim.
2. **Attribution travels with any export.** Any path that emits data emits its
   attribution with it.
3. **Provenance is recorded.** Every mirror stores when it was built, from what source,
   and the SHA-256 of each source file, readable via `collective status`. A mirror
   can always say what it is a copy of.
4. **No claim is made over the data.** The Apache-2.0 grant covers this repository's
   code only. Nothing here relicenses, sublicenses, or asserts ownership of Learning
   Commons' work.

## How the data is obtained

Learning Commons publishes complete versioned exports on a **public CDN**, documented
at [Local files](https://docs.learningcommons.org/knowledge-graph/using-knowledge-graph/local-files):

```
https://cdn.learningcommons.org/knowledge-graph/v1.12.0/exports/nodes.jsonl
https://cdn.learningcommons.org/knowledge-graph/v1.12.0/exports/relationships.jsonl
```

No API key, no account, no request form. `collective init` fetches exactly these URLs
and passes upstream's own `ref` parameter so the traffic is identifiable as a mirror
rather than as scraping.

**A distinction worth keeping clear:** their authenticated MCP API at
`kg.mcp.learningcommons.org` is a *separate surface*, governed by whatever agreement
attaches to your key. Collective does not use it. Everything here comes from the
public CDN under the terms CC BY-4.0 already grants.

`build` never touches the network at all, so if you prefer to obtain the export another
way, drop the files in and run `build` on them — the rest of the pipeline does not care
how they arrived.

## If you deploy a mirror

You inherit the attribution obligation. It is met by default — leave the property bags
intact and surface the attribution wherever you surface the data. If you build a UI on
top, show the jurisdiction's attribution alongside its standards.

## If you are Learning Commons

If any part of this misreads your intent, licensing, or terms, open an issue and it
will be corrected promptly. The goal is to be a well-behaved downstream, and getting
attribution right is the least this project owes you.
