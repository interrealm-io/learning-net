"""Query layer over a Learning Net mirror.

This module knows about the Learning Commons graph and nothing about transports.
The MCP server, the HTTP API, and the CLI all sit on top of it — which is what
keeps them from drifting apart. If a query belongs to more than one surface, it
belongs here.

THREE TOPOLOGY FACTS THAT DECIDE WHETHER A QUERY RETURNS ANYTHING
-----------------------------------------------------------------
These are properties of the published graph, not of this code. Every one of
them was found by a query returning empty when it obviously should not have.

1. Standard codes are not unique. `4.OA.A.3` matches 26 nodes — one per
   jurisdiction that adopted Common Core, plus the Multi-State original.

2. Progressions exist only on the Multi-State mathematics spine. All 757
   `buildsTowards` edges are Multi-State / Mathematics. No state standard has
   one directly and no ELA, Science, or Social Studies standard has one at all.

3. Alignment is hub-and-spoke. States link to Multi-State, never to each other.
   All 52,807 curriculum alignments likewise target Multi-State Mathematics.

So progression and curriculum lookups on a state standard MUST bridge through
the aligned Multi-State standard, and a state-to-state crosswalk is two hops.
Every method that bridges says so in its result, so a caller can always tell
inference from ground truth.
"""

from __future__ import annotations

import collections
import json
import re
import sqlite3

NODE_COLS = (
    "id, label, name, statement_code, case_uuid, jurisdiction, subject, "
    "grade_level, statement_type, description"
)
_N = ", ".join("n." + c.strip() for c in NODE_COLS.split(","))

MULTI_STATE = "Multi-State"


class GraphError(Exception):
    """A query that cannot be answered — bad reference, empty mirror."""


def _grade(v):
    """gradeLevel arrives as a JSON array string like '["4"]'. Flatten it."""
    if not v:
        return None
    try:
        g = json.loads(v)
        return ",".join(map(str, g)) if isinstance(g, list) else str(g)
    except (ValueError, TypeError):
        return str(v)


def _brief(r):
    out = {
        "id": r["id"],
        "label": r["label"],
        "statementCode": r["statement_code"],
        "jurisdiction": r["jurisdiction"],
        "subject": r["subject"],
        "gradeLevel": _grade(r["grade_level"]),
        "statementType": r["statement_type"],
        "caseIdentifierUUID": r["case_uuid"],
    }
    text = r["description"] or r["name"]
    if text:
        out["statement"] = text
    return {k: v for k, v in out.items() if v is not None}


def _fts_query(q):
    """FTS5 MATCH is a query language. Quote bare terms so user text is literal."""
    terms = re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-']*", q)
    if not terms:
        raise GraphError(f"no searchable terms in {q!r}")
    return " ".join(f'"{t}"' for t in terms)


class Graph:
    """Read-only access to a built mirror."""

    def __init__(self, db_path):
        self.db_path = str(db_path)
        try:
            self.con = sqlite3.connect(
                f"file:{self.db_path}?mode=ro", uri=True, check_same_thread=False
            )
        except sqlite3.OperationalError as e:
            raise GraphError(
                f"cannot open mirror at {self.db_path}: {e}. Run `learning-net build` first."
            ) from e
        self.con.row_factory = sqlite3.Row

    # -- primitives ---------------------------------------------------------

    def _rows(self, sql, params=()):
        return self.con.execute(sql, params).fetchall()

    def resolve(self, ref):
        """Accept an internal id, a caseIdentifierUUID, or a statement code.

        Callers should never have to know which kind of identifier they hold;
        that knowledge is exactly the friction this project exists to remove.
        """
        if not ref:
            return []
        for col in ("id", "case_uuid", "statement_code"):
            hits = self._rows(f"SELECT {NODE_COLS} FROM nodes WHERE {col} = ?", (ref,))
            if hits:
                return hits
        return []

    def _one(self, ref):
        hits = self.resolve(ref)
        if not hits:
            raise GraphError(
                f"no node matches {ref!r} — try find_standard or search_standards first"
            )
        return hits[0]

    def _aligned(self, node_id):
        """Standards joined by hasStandardAlignment, in either direction."""
        return self._rows(
            f"SELECT {_N} FROM edges e JOIN nodes n ON n.id = e.dst "
            "WHERE e.src = ? AND e.label = 'hasStandardAlignment' "
            f"UNION SELECT {_N} FROM edges e JOIN nodes n ON n.id = e.src "
            "WHERE e.dst = ? AND e.label = 'hasStandardAlignment'",
            (node_id, node_id),
        )

    def _spine_anchors(self, node):
        """Nodes on the Multi-State spine that carry this standard's edges.

        Returns (anchors, bridged). Progression and curriculum edges hang off
        the spine, so a state standard reaches them only through its alignment.
        """
        if node["jurisdiction"] == MULTI_STATE:
            return [node], False
        anchors = [a for a in self._aligned(node["id"]) if a["jurisdiction"] == MULTI_STATE]
        return anchors, bool(anchors)

    # -- queries ------------------------------------------------------------

    def find_standard(self, statement_code, jurisdiction=None, subject=None, limit=25):
        sql = f"SELECT {NODE_COLS} FROM nodes WHERE statement_code = ?"
        p = [statement_code]
        if jurisdiction:
            sql += " AND jurisdiction = ?"
            p.append(jurisdiction)
        if subject:
            sql += " AND subject = ?"
            p.append(subject)
        sql += " ORDER BY (jurisdiction = 'Multi-State') DESC, jurisdiction LIMIT ?"
        p.append(limit)
        found = self._rows(sql, p)
        return {
            "query": {
                "statementCode": statement_code,
                "jurisdiction": jurisdiction,
                "subject": subject,
            },
            "matchCount": len(found),
            "note": (
                "The same code is reused across jurisdictions; 'Multi-State' is the "
                "Common Core / NGSS spine and is listed first."
            )
            if len(found) > 1
            else None,
            "standards": [_brief(r) for r in found],
        }

    def search_standards(
        self, query, jurisdiction=None, subject=None, grade_level=None, limit=20
    ):
        sql = (
            f"SELECT {_N}, bm25(nodes_fts) AS rank FROM nodes_fts f "
            "JOIN nodes n ON n.id = f.id WHERE nodes_fts MATCH ?"
        )
        p = [_fts_query(query)]
        if jurisdiction:
            sql += " AND n.jurisdiction = ?"
            p.append(jurisdiction)
        if subject:
            sql += " AND n.subject = ?"
            p.append(subject)
        if grade_level:
            sql += " AND n.grade_level LIKE ?"
            p.append(f'%"{grade_level}"%')
        sql += " ORDER BY rank LIMIT ?"
        p.append(limit)
        found = self._rows(sql, p)
        return {
            "query": query,
            "resultCount": len(found),
            "results": [_brief(r) for r in found],
        }

    def learning_components(self, standard):
        n = self._one(standard)
        comps = self._rows(
            f"SELECT {_N} FROM edges e JOIN nodes n ON n.id = e.src "
            "WHERE e.dst = ? AND e.label = 'supports' AND e.src_label = 'LearningComponent'",
            (n["id"],),
        )
        return {
            "standard": _brief(n),
            "componentCount": len(comps),
            "learningComponents": [
                {"id": c["id"], "component": c["description"], "subject": c["subject"]}
                for c in comps
            ],
        }

    def progression(self, standard, direction="backward", limit=25):
        if direction not in ("backward", "forward"):
            raise GraphError("direction must be 'backward' or 'forward'")
        n = self._one(standard)
        anchors, bridged = self._spine_anchors(n)

        if direction == "backward":
            sql = (
                f"SELECT {_N} FROM edges e JOIN nodes n ON n.id = e.src "
                "WHERE e.dst = ? AND e.label = 'buildsTowards' LIMIT ?"
            )
        else:
            sql = (
                f"SELECT {_N} FROM edges e JOIN nodes n ON n.id = e.dst "
                "WHERE e.src = ? AND e.label = 'buildsTowards' LIMIT ?"
            )

        seen, out = set(), []
        for a in anchors:
            for r in self._rows(sql, (a["id"], limit)):
                if r["id"] in seen:
                    continue
                seen.add(r["id"])
                entry = _brief(r)
                if bridged:
                    local = [
                        x for x in self._aligned(r["id"])
                        if x["jurisdiction"] == n["jurisdiction"]
                    ]
                    if local:
                        entry["equivalentInJurisdiction"] = [_brief(x) for x in local]
                out.append(entry)

        return {
            "standard": _brief(n),
            "direction": direction,
            "bridgedViaMultiState": bridged,
            "anchors": [_brief(a) for a in anchors] if bridged else None,
            "resultCount": len(out),
            "note": (
                "No buildsTowards edges reach this standard. Progressions are authored "
                "only for Multi-State Mathematics, so most ELA, Science, and Social "
                "Studies standards have none."
            )
            if not out
            else None,
            "progression": out,
        }

    def crosswalk(self, standard, to_jurisdiction=None, limit=60):
        n = self._one(standard)
        direct = self._aligned(n["id"])
        two_hop = False

        if to_jurisdiction and to_jurisdiction != MULTI_STATE:
            hit = [a for a in direct if a["jurisdiction"] == to_jurisdiction]
            if not hit:
                hub, _ = self._spine_anchors(n)
                seen, hit = set(), []
                for h in hub:
                    for a in self._aligned(h["id"]):
                        if a["jurisdiction"] == to_jurisdiction and a["id"] not in seen:
                            seen.add(a["id"])
                            hit.append(a)
                two_hop = bool(hit)
            al = hit
        elif to_jurisdiction:
            al = [a for a in direct if a["jurisdiction"] == to_jurisdiction]
        else:
            al = direct

        return {
            "standard": _brief(n),
            "viaMultiStateHub": two_hop,
            "alignmentCount": len(al),
            "note": (
                "No alignment found. Alignments are hub-and-spoke through 'Multi-State' "
                "— a state standard with no Multi-State link cannot be crosswalked."
            )
            if not al
            else None,
            "alignedStandards": [_brief(a) for a in al[:limit]],
        }

    def resolve_jurisdiction(self, name):
        """Match a jurisdiction name loosely. Returns (canonical, suggestions)."""
        if not name:
            return None, []
        known = self.jurisdictions()
        lowered = {j.lower(): j for j in known}
        if name.lower() in lowered:
            return lowered[name.lower()], []
        near = [j for j in known if name.lower() in j.lower() or j.lower() in name.lower()]
        return None, near[:5] or known[:8]

    def verify_alignment_claim(self, statement_code, jurisdiction, subject=None):
        """Is an alignment claim addressable in a given jurisdiction?

        This is the question nobody can currently answer, and it is the reason
        "standards-aligned" functions as marketing rather than as a checkable
        assertion. A vendor says its material aligns to `4.OA.A.3`. A Texas
        district has no way to discover that Texas never adopted that code —
        the standard it names does not exist in the curriculum the district is
        legally accountable to.

        The check itself is trivial once the graph is local. It is only hard
        because it requires knowing that codes are not unique across
        jurisdictions, and that is exactly the knowledge the person asking does
        not have. So the tool encodes it and answers in plain language.

        Verdicts:
          addressable            the code exists in that jurisdiction
          equivalent_exists      it does not, but an aligned local standard does
          not_addressable        it does not, and nothing local aligns to it
          unknown_code           the code is not in the graph at all
          unknown_jurisdiction   the jurisdiction name was not recognised
        """
        canon, suggestions = self.resolve_jurisdiction(jurisdiction)
        if not canon:
            return {
                "claim": {"statementCode": statement_code, "jurisdiction": jurisdiction},
                "verdict": "unknown_jurisdiction",
                "plainLanguage": (
                    f"{jurisdiction!r} is not a jurisdiction in this mirror. "
                    f"Did you mean one of: {', '.join(suggestions)}?"
                ),
                "suggestions": suggestions,
            }

        sql = f"SELECT {NODE_COLS} FROM nodes WHERE statement_code = ?"
        params = [statement_code]
        if subject:
            sql += " AND subject = ?"
            params.append(subject)
        matches = self._rows(sql, params)

        if not matches:
            return {
                "claim": {"statementCode": statement_code, "jurisdiction": canon},
                "verdict": "unknown_code",
                "plainLanguage": (
                    f"No standard with the code {statement_code!r} exists anywhere in this "
                    f"mirror, in any of the {len(self.jurisdictions())} jurisdictions it "
                    f"covers. The claim cannot be checked because the code it cites is not "
                    f"a real standard code. Try search_standards to find what was meant."
                ),
            }

        defined_in = sorted({m["jurisdiction"] for m in matches if m["jurisdiction"]})
        exact = [m for m in matches if m["jurisdiction"] == canon]

        if exact:
            return {
                "claim": {"statementCode": statement_code, "jurisdiction": canon},
                "verdict": "addressable",
                "plainLanguage": (
                    f"Verified. {statement_code} is a real standard in {canon}, so material "
                    f"claiming alignment to it is making a checkable claim about this "
                    f"jurisdiction's curriculum."
                ),
                "standard": _brief(exact[0]),
                "alsoDefinedIn": [j for j in defined_in if j != canon][:25],
                "definedInCount": len(defined_in),
            }

        # The code is real, but not in this jurisdiction. Bridge to a local
        # equivalent through the Multi-State spine.
        anchor = next((m for m in matches if m["jurisdiction"] == MULTI_STATE), matches[0])
        cross = self.crosswalk(anchor["id"], to_jurisdiction=canon)
        equivalents = cross["alignedStandards"]
        common_core = MULTI_STATE in defined_in

        if equivalents:
            return {
                "claim": {"statementCode": statement_code, "jurisdiction": canon},
                "verdict": "equivalent_exists",
                "plainLanguage": (
                    f"{statement_code} is NOT a standard in {canon}"
                    + (
                        " — it is a Multi-State (Common Core / NGSS) code, which "
                        f"{canon} did not adopt under that identifier. "
                        if common_core
                        else f", though it is used in {len(defined_in)} other jurisdiction(s). "
                    )
                    + f"Material citing it is not naming anything in {canon}'s curriculum. "
                    f"The closest {canon} standard(s) covering the same content: "
                    + ", ".join(
                        e.get("statementCode") or e["id"][:8] for e in equivalents[:5]
                    )
                    + ". Ask the vendor to restate the alignment using those codes."
                ),
                "citedStandard": _brief(anchor),
                "localEquivalents": equivalents[:10],
                "bridgedViaMultiState": cross["viaMultiStateHub"],
                "definedIn": defined_in[:25],
            }

        return {
            "claim": {"statementCode": statement_code, "jurisdiction": canon},
            "verdict": "not_addressable",
            "plainLanguage": (
                f"{statement_code} is NOT a standard in {canon}, and no {canon} standard "
                f"is aligned to it in this graph. It is defined in: "
                f"{', '.join(defined_in[:8])}. A claim of alignment to this code says "
                f"nothing verifiable about {canon}'s curriculum. Note that absence of an "
                f"alignment edge is not proof the content is unrelated — only that no "
                f"published alignment exists to check against."
            ),
            "citedStandard": _brief(anchor),
            "definedIn": defined_in[:25],
        }

    def context(self, standard, max_depth=6, child_limit=40):
        n = self._one(standard)
        ancestors, cur = [], n["id"]
        for _ in range(max_depth):
            p = self._rows(
                f"SELECT {_N} FROM edges e JOIN nodes n ON n.id = e.src "
                "WHERE e.dst = ? AND e.label = 'hasChild' LIMIT 1",
                (cur,),
            )
            if not p:
                break
            ancestors.append(_brief(p[0]))
            cur = p[0]["id"]
        kids = self._rows(
            f"SELECT {_N} FROM edges e JOIN nodes n ON n.id = e.dst "
            "WHERE e.src = ? AND e.label = 'hasChild' LIMIT ?",
            (n["id"], child_limit),
        )
        return {
            "standard": _brief(n),
            "ancestors": ancestors,
            "childCount": len(kids),
            "children": [_brief(k) for k in kids],
        }

    def curriculum(self, standard, kind=None, limit=40):
        n = self._one(standard)
        anchors, bridged = self._spine_anchors(n)
        sql = (
            f"SELECT {_N} FROM edges e JOIN nodes n ON n.id = e.src "
            "WHERE e.dst = ? AND e.label = 'hasEducationalAlignment'"
        )
        if kind:
            sql += " AND n.label = ?"
        sql += " LIMIT ?"

        seen, items = set(), []
        for a in anchors:
            p = [a["id"]] + ([kind] if kind else []) + [limit]
            for i in self._rows(sql, p):
                if i["id"] in seen:
                    continue
                seen.add(i["id"])
                items.append(i)

        return {
            "standard": _brief(n),
            "bridgedViaMultiState": bridged,
            "itemCount": len(items),
            "note": (
                "No curriculum is aligned to this standard. All curriculum alignments "
                "target Multi-State Mathematics, so non-math standards have none."
            )
            if not items
            else None,
            "curriculum": [
                {
                    "id": i["id"],
                    "type": i["label"],
                    "name": i["name"],
                    "gradeLevel": _grade(i["grade_level"]),
                    "subject": i["subject"],
                }
                for i in items
            ],
        }

    def _ids_by_jurisdiction(self, sql, params=()):
        """Collect {jurisdiction: {standard ids}} for an edge-participation query."""
        out = collections.defaultdict(set)
        for j, i in self._rows(sql, params):
            if j:
                out[j].add(i)
        return out

    def coverage_report(self, subject=None):
        """How much of each jurisdiction's curriculum is actually connected.

        The alignment layer is what makes a cross-jurisdiction claim checkable
        at all. Publishing 258,000 standards is only half of it — if a state's
        standards carry no alignment edges, then for that state no alignment
        claim can be verified in either direction, and no amount of local
        tooling fixes that.

        Nobody currently publishes this measurement, including upstream. It is
        the most useful thing a mirror can compute and hand back: not a
        criticism, a work list.

        Four independent dimensions, each reported as "how many of this
        jurisdiction's standards participate in this kind of edge at all":

          crosswalk    hasStandardAlignment  -> can this be translated?
          components   supports              -> is it broken into teachable skills?
          curriculum   hasEducationalAlignment -> is there material aligned to it?
          progression  buildsTowards         -> does it have prerequisites?
        """
        where = " WHERE label='StandardsFrameworkItem'"
        params = []
        if subject:
            where += " AND subject = ?"
            params.append(subject)

        totals = {
            j: n
            for j, n in self._rows(
                f"SELECT jurisdiction, COUNT(*) FROM nodes{where} "
                "AND jurisdiction IS NOT NULL GROUP BY 1",
                params,
            )
        }

        subj_filter = " AND n.subject = ?" if subject else ""
        sp = [subject] if subject else []

        def both_directions(label):
            return self._ids_by_jurisdiction(
                "SELECT n.jurisdiction, n.id FROM edges e JOIN nodes n ON n.id = e.src "
                f"WHERE e.label = ? AND n.label='StandardsFrameworkItem'{subj_filter} "
                "UNION "
                "SELECT n.jurisdiction, n.id FROM edges e JOIN nodes n ON n.id = e.dst "
                f"WHERE e.label = ? AND n.label='StandardsFrameworkItem'{subj_filter}",
                [label, *sp, label, *sp],
            )

        def incoming(label, src_label=None):
            sql = (
                "SELECT n.jurisdiction, n.id FROM edges e JOIN nodes n ON n.id = e.dst "
                f"WHERE e.label = ? AND n.label='StandardsFrameworkItem'{subj_filter}"
            )
            p = [label, *sp]
            if src_label:
                sql += " AND e.src_label = ?"
                p.append(src_label)
            return self._ids_by_jurisdiction(sql, p)

        crosswalk = both_directions("hasStandardAlignment")
        progression = both_directions("buildsTowards")
        components = incoming("supports", "LearningComponent")
        curriculum = incoming("hasEducationalAlignment")

        def pct(n, d):
            return round(100 * n / d, 1) if d else 0.0

        rows_out = []
        for j, total in totals.items():
            c, k = len(crosswalk.get(j, ())), len(components.get(j, ()))
            cu, pr = len(curriculum.get(j, ())), len(progression.get(j, ()))
            rows_out.append(
                {
                    "jurisdiction": j,
                    "standards": total,
                    "crosswalked": c,
                    "crosswalkPct": pct(c, total),
                    "withComponents": k,
                    "componentsPct": pct(k, total),
                    "withCurriculum": cu,
                    "withProgression": pr,
                    "isolated": c == 0,
                }
            )
        rows_out.sort(key=lambda r: (r["crosswalkPct"], -r["standards"]))

        isolated = [r["jurisdiction"] for r in rows_out if r["isolated"]]
        total_standards = sum(totals.values())
        total_crosswalked = sum(len(v) for v in crosswalk.values())
        covered = [r["crosswalkPct"] for r in rows_out if not r["isolated"]]

        return {
            "subject": subject,
            "generatedFrom": self.snapshot_info(),
            "national": {
                "jurisdictions": len(totals),
                "standards": total_standards,
                "crosswalked": total_crosswalked,
                "crosswalkPct": pct(total_crosswalked, total_standards),
                "jurisdictionsWithNoCrosswalk": len(isolated),
                "isolatedJurisdictions": isolated,
                "standardsInIsolatedJurisdictions": sum(
                    r["standards"] for r in rows_out if r["isolated"]
                ),
                "medianCrosswalkPctWhereAny": (
                    round(sorted(covered)[len(covered) // 2], 1) if covered else 0.0
                ),
            },
            "interpretation": (
                f"{len(isolated)} of {len(totals)} jurisdictions have no alignment edges at "
                f"all, covering {sum(r['standards'] for r in rows_out if r['isolated']):,} "
                f"standards. For those, an alignment claim cannot be verified in either "
                f"direction. Across jurisdictions that do have alignment, coverage is thin — "
                f"only {pct(total_crosswalked, total_standards)}% of all standards carry one. "
                f"This measures the alignment layer, not the standards themselves, which are "
                f"complete."
            ),
            "byJurisdiction": rows_out,
        }

    def node(self, ref):
        r = self._rows(
            "SELECT id, label, props FROM nodes WHERE id = ? OR case_uuid = ?", (ref, ref)
        )
        if not r:
            raise GraphError(f"no node with id {ref!r}")
        return {"id": r[0]["id"], "label": r[0]["label"], "properties": json.loads(r[0]["props"])}

    def stats(self):
        def counts(sql):
            return {r[0]: r[1] for r in self._rows(sql)}

        return {
            "nodesByLabel": counts(
                "SELECT label, COUNT(*) FROM nodes GROUP BY 1 ORDER BY 2 DESC"
            ),
            "edgesByLabel": counts(
                "SELECT label, COUNT(*) FROM edges GROUP BY 1 ORDER BY 2 DESC"
            ),
            "jurisdictions": counts(
                "SELECT jurisdiction, COUNT(*) FROM nodes "
                "WHERE label='StandardsFrameworkItem' GROUP BY 1 ORDER BY 2 DESC"
            ),
            "subjects": counts(
                "SELECT subject, COUNT(*) FROM nodes "
                "WHERE label='StandardsFrameworkItem' GROUP BY 1 ORDER BY 2 DESC"
            ),
            "snapshot": self.snapshot_info(),
        }

    def snapshot_info(self):
        """Provenance of the mirror: when it was built and from what.

        A mirror that cannot say how stale it is has no business being trusted,
        so this is part of the contract rather than a nicety.
        """
        try:
            rows = self._rows("SELECT key, value FROM meta")
        except sqlite3.OperationalError:
            return None
        return {r["key"]: r["value"] for r in rows}

    def jurisdictions(self):
        return [
            r[0]
            for r in self._rows(
                "SELECT DISTINCT jurisdiction FROM nodes WHERE jurisdiction IS NOT NULL "
                "ORDER BY (jurisdiction = 'Multi-State') DESC, jurisdiction"
            )
        ]

    def close(self):
        self.con.close()
