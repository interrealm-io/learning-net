"""Query layer over a Collective mirror.

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


def _grade_list(v):
    """gradeLevel as a list of individual grade strings."""
    g = _grade(v)
    return g.split(",") if g else []


_GRADE_ORDINALS = {"PK": -1, "PRE-K": -1, "PREK": -1, "TK": -1, "K": 0, "KG": 0}


def _grade_ordinal(g):
    """'K' -> 0, '5' -> 5, unparseable -> None. For ordering and comparison."""
    if g is None:
        return None
    g = str(g).strip().upper()
    if g in _GRADE_ORDINALS:
        return _GRADE_ORDINALS[g]
    try:
        return int(g)
    except ValueError:
        return None


def _grade_sort_key(g):
    o = _grade_ordinal(str(g).split(",")[0])
    return (o is None, o if o is not None else 0, str(g))


def _examples(props_json):
    """The worked examples on a LearningComponent, if any.

    Upstream stores them as a JSON-encoded string inside the property bag
    ('examples': '["big ball"]'), so this decodes twice.
    """
    try:
        ex = json.loads(props_json).get("examples")
        if isinstance(ex, str):
            ex = json.loads(ex)
        return ex if isinstance(ex, list) and ex else None
    except (ValueError, TypeError, AttributeError):
        return None


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
                f"cannot open mirror at {self.db_path}: {e}. Run `collective build` first."
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
            # A bare code matches one node per adopting jurisdiction; the spine
            # sorts first so an undisambiguated lookup lands where the graph's
            # connectivity actually is, not on an arbitrary state.
            hits = self._rows(
                f"SELECT {NODE_COLS} FROM nodes WHERE {col} = ? "
                "ORDER BY (jurisdiction = 'Multi-State') DESC, jurisdiction",
                (ref,),
            )
            if hits:
                return hits
        return []

    def _one(self, ref, jurisdiction=None):
        hits = self.resolve(ref)
        if jurisdiction and hits:
            canon, _ = self.resolve_jurisdiction(jurisdiction)
            wanted = [h for h in hits if h["jurisdiction"] == (canon or jurisdiction)]
            if not wanted:
                raise GraphError(
                    f"{ref!r} matches no standard in {jurisdiction!r} — it exists in: "
                    + ", ".join(sorted({h['jurisdiction'] or '?' for h in hits})[:8])
                )
            hits = wanted
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

    def _with_descendants(self, node, depth=3):
        """The node plus its hasChild descendants, breadth-first, bounded."""
        out, frontier = [node], [node]
        for _ in range(depth):
            nxt = []
            for f in frontier:
                nxt += self._rows(
                    f"SELECT {_N} FROM edges e JOIN nodes n ON n.id = e.dst "
                    "WHERE e.src = ? AND e.label = 'hasChild'",
                    (f["id"],),
                )
            if not nxt:
                break
            out += nxt
            frontier = nxt
        return out

    def _components_of(self, root):
        """(component_row, supporting_standard) pairs for root and its descendants.

        Components attach to the finest-grained standard — often a lettered
        child like L.2.1.e — so asking the parent must look downward too.
        """
        out, seen = [], set()
        for s in self._with_descendants(root):
            for c in self._rows(
                f"SELECT {_N}, n.props FROM edges e JOIN nodes n ON n.id = e.src "
                "WHERE e.dst = ? AND e.label = 'supports' "
                "AND e.src_label = 'LearningComponent'",
                (s["id"],),
            ):
                if c["id"] not in seen:
                    seen.add(c["id"])
                    out.append((c, s))
        return out

    def learning_components(self, standard, jurisdiction=None):
        n = self._one(standard, jurisdiction)
        pairs, bridged = self._components_of(n), False
        if not pairs and n["jurisdiction"] != MULTI_STATE:
            # Component edges exist for only some jurisdictions. The rest reach
            # them the same way progressions do: through the Multi-State spine.
            anchors, _ = self._spine_anchors(n)
            seen = set()
            for a in anchors:
                for c, s in self._components_of(a):
                    if c["id"] not in seen:
                        seen.add(c["id"])
                        pairs.append((c, s))
            bridged = bool(pairs)

        comps = []
        for c, s in pairs:
            entry = {"id": c["id"], "component": c["description"], "subject": c["subject"]}
            ex = _examples(c["props"])
            if ex:
                entry["examples"] = ex
            if s["id"] != n["id"]:
                entry["supportsStandard"] = s["statement_code"] or s["id"]
            comps.append(entry)

        return {
            "standard": _brief(n),
            "componentCount": len(comps),
            "bridgedViaMultiState": bridged,
            "note": (
                "No learning components reach this standard, its children, or its "
                "Multi-State equivalent. Component coverage varies by subject and "
                "grade — use search_learning_components to find what exists for a "
                "topic, or coverage_report for the map."
            )
            if not comps
            else None,
            "learningComponents": comps,
        }

    def list_standards(
        self, jurisdiction=None, subject=None, grade_level=None, limit=100, offset=0
    ):
        """Faceted browse: pick a state, a grade, a subject — no search text needed.

        The drill-down entry point search_standards cannot be, because FTS
        requires words to match. Facet counts describe the whole filtered set,
        so a UI can offer the next narrowing step without a second query.
        """
        if not (jurisdiction or subject or grade_level):
            raise GraphError(
                "pass at least one of jurisdiction, subject, or gradeLevel — "
                "listing all 258k standards helps nobody"
            )
        where, p = ["label = 'StandardsFrameworkItem'"], []
        if jurisdiction:
            canon, suggestions = self.resolve_jurisdiction(jurisdiction)
            if not canon:
                raise GraphError(
                    f"unknown jurisdiction {jurisdiction!r} — did you mean: "
                    f"{', '.join(suggestions)}?"
                )
            jurisdiction = canon
            where.append("jurisdiction = ?")
            p.append(canon)
        if subject:
            where.append("subject = ?")
            p.append(subject)
        if grade_level:
            where.append("grade_level LIKE ?")
            p.append(f'%"{grade_level}"%')
        w = " AND ".join(where)

        total = self._rows(f"SELECT COUNT(*) FROM nodes WHERE {w}", p)[0][0]
        subjects = dict(
            self._rows(
                f"SELECT subject, COUNT(*) FROM nodes WHERE {w} "
                "AND subject IS NOT NULL GROUP BY 1 ORDER BY 2 DESC",
                p,
            )
        )
        grades = collections.Counter()
        for gl, cnt in self._rows(
            f"SELECT grade_level, COUNT(*) FROM nodes WHERE {w} "
            "AND grade_level IS NOT NULL GROUP BY 1",
            p,
        ):
            grades[_grade(gl)] += cnt
        grades = dict(sorted(grades.items(), key=lambda kv: _grade_sort_key(kv[0])))

        rows = self._rows(
            f"SELECT {NODE_COLS}, (SELECT COUNT(*) FROM edges e WHERE e.dst = nodes.id "
            "AND e.label = 'supports' AND e.src_label = 'LearningComponent') AS lc_count "
            f"FROM nodes WHERE {w} "
            "ORDER BY subject, statement_code IS NULL, statement_code LIMIT ? OFFSET ?",
            p + [limit, offset],
        )
        out = []
        for r in rows:
            b = _brief(r)
            if r["lc_count"]:
                b["learningComponentCount"] = r["lc_count"]
            out.append(b)

        return {
            "filters": {
                "jurisdiction": jurisdiction,
                "subject": subject,
                "gradeLevel": grade_level,
            },
            "totalCount": total,
            "returned": len(out),
            "offset": offset,
            "facets": {"subjects": subjects, "gradeLevels": grades},
            "standards": out,
        }

    def search_learning_components(
        self, query, jurisdiction=None, grade_level=None, limit=30
    ):
        """Search the granular skills themselves, mapped back to standards.

        Learning components carry no grade or jurisdiction of their own — both
        are derivable only through the standards they support. So each hit is
        mapped to supporting standards (in the requested jurisdiction where
        possible, bridging via the Multi-State hub where not) and, when a grade
        is given, labelled at/below/above it. Below-grade hits are foundational
        skills for the topic, not noise: a 5th grader studying adjectives needs
        the K-2 components, because that is where upstream authored them.
        """
        canon = None
        if jurisdiction:
            canon, suggestions = self.resolve_jurisdiction(jurisdiction)
            if not canon:
                raise GraphError(
                    f"unknown jurisdiction {jurisdiction!r} — did you mean: "
                    f"{', '.join(suggestions)}?"
                )
        want = _grade_ordinal(grade_level) if grade_level else None

        hits = self._rows(
            f"SELECT {_N}, n.props FROM nodes_fts f JOIN nodes n ON n.id = f.id "
            "WHERE nodes_fts MATCH ? AND n.label = 'LearningComponent' "
            "ORDER BY bm25(nodes_fts) LIMIT ?",
            (_fts_query(query), limit),
        )

        out, unmapped = [], 0
        for lc in hits:
            supported = self._rows(
                f"SELECT {_N} FROM edges e JOIN nodes n ON n.id = e.dst "
                "WHERE e.src = ? AND e.label = 'supports'",
                (lc["id"],),
            )
            via_ms = False
            local = [s for s in supported if s["jurisdiction"] == canon] if canon else supported
            if canon and not local:
                # No direct edge into this state. Map the Multi-State targets
                # down through alignment — trying each target's parent too,
                # since alignments are often authored at the parent standard.
                seen, candidates = set(), []
                for s in supported:
                    if s["jurisdiction"] != MULTI_STATE:
                        continue
                    candidates.append(s)
                    candidates += self._rows(
                        f"SELECT {_N} FROM edges e JOIN nodes n ON n.id = e.src "
                        "WHERE e.dst = ? AND e.label = 'hasChild' LIMIT 1",
                        (s["id"],),
                    )
                for cand in candidates:
                    for a in self._aligned(cand["id"]):
                        if a["jurisdiction"] == canon and a["id"] not in seen:
                            seen.add(a["id"])
                            local.append(a)
                via_ms = bool(local)
            if canon and not local:
                unmapped += 1
                continue

            grades = sorted(
                {g for s in local for g in _grade_list(s["grade_level"])},
                key=_grade_sort_key,
            )
            entry = {
                "id": lc["id"],
                "component": lc["description"],
                "subject": lc["subject"],
            }
            ex = _examples(lc["props"])
            if ex:
                entry["examples"] = ex
            if grades:
                entry["gradeLevels"] = grades
            if want is not None:
                ords = [o for o in map(_grade_ordinal, grades) if o is not None]
                if ords:
                    if want in ords:
                        entry["gradeRelation"] = "at"
                    elif max(ords) < want:
                        entry["gradeRelation"] = "below"
                    elif min(ords) > want:
                        entry["gradeRelation"] = "above"
                    else:
                        entry["gradeRelation"] = "spans"
            entry["supportsStandards"] = [_brief(s) for s in local[:6]]
            if via_ms:
                entry["viaMultiStateHub"] = True
            out.append(entry)

        rank = {"at": 0, "spans": 1, "below": 2, "above": 3}
        if want is not None:
            out.sort(key=lambda e: rank.get(e.get("gradeRelation"), 4))
        at_grade = sum(1 for e in out if e.get("gradeRelation") == "at")

        return {
            "query": query,
            "jurisdiction": canon,
            "gradeLevel": grade_level,
            "resultCount": len(out),
            "unmappedCount": unmapped or None,
            "note": (
                f"No components for this topic are authored at grade "
                f"{grade_level}. The below-grade results are the foundational "
                f"skills for the topic — appropriate source material for review "
                f"and study aids, per standard practice on unfinished learning."
            )
            if want is not None and out and not at_grade
            else (
                f"{unmapped} component(s) matched but support no standard in "
                f"{canon}, directly or via the Multi-State hub, and were omitted."
                if unmapped
                else None
            ),
            "components": out,
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
