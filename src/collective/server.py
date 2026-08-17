"""MCP server over a Collective mirror.

Speaks MCP over stdio with nothing but the standard library — no SDK, no pip
install, no network. That constraint is deliberate: the point of a mirror is
that a school can run it on hardware and a Python install it already has.

All eleven tools are thin wrappers over `graph.Graph`. The HTTP API serves the
same methods, so the two surfaces cannot drift.
"""

from __future__ import annotations

import json
import os
import sys

from .graph import Graph, GraphError

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "collective"
SERVER_VERSION = "0.1.0"

INSTRUCTIONS = (
    "A self-hosted mirror of the Learning Commons Knowledge Graph: K-12 academic "
    "standards across every US jurisdiction, the learning components that support "
    "them, alignments between jurisdictions, and aligned curriculum. "
    "Standard codes are NOT unique across jurisdictions — always pass a jurisdiction "
    "when the user means a specific state. Call graph_stats first to see coverage and "
    "how stale this mirror is."
)

TOOLS = [
    {
        "name": "graph_stats",
        "description": (
            "Shape and provenance of this mirror: node and edge counts by label, "
            "coverage by jurisdiction and subject, and when it was last synced. "
            "Call first to see what is available and how current it is."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "verify_alignment_claim",
        "description": (
            "Check whether an alignment claim is addressable in a specific jurisdiction. "
            "Use this whenever anyone asserts that material, a lesson, a product, or AI "
            "output is 'aligned to' a standard code for a particular state. Standard codes "
            "are NOT unique across jurisdictions and many states never adopted the "
            "Common Core codes at all, so a claim of alignment to e.g. '4.OA.A.3' names "
            "nothing real in Texas. Returns a verdict — addressable, equivalent_exists, "
            "not_addressable, unknown_code, unknown_jurisdiction — with a plain-language "
            "explanation suitable for a district administrator, plus the local equivalent "
            "standards to ask the vendor to restate against."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "statementCode": {
                    "type": "string",
                    "description": "The standard code being claimed, e.g. '4.OA.A.3'",
                },
                "jurisdiction": {
                    "type": "string",
                    "description": "The state or territory the claim is being made to, e.g. 'Texas'",
                },
                "subject": {"type": "string"},
            },
            "required": ["statementCode", "jurisdiction"],
        },
    },
    {
        "name": "coverage_report",
        "description": (
            "Measure how much of each jurisdiction's curriculum is actually CONNECTED — "
            "how many of its standards carry cross-jurisdiction alignments, learning "
            "components, aligned curriculum, or progressions. Use this to answer 'can "
            "alignment claims be verified for my state at all?' and to see where the "
            "graph's connective tissue is missing. Nobody publishes this measurement, "
            "including upstream. Reports worst-covered jurisdictions first."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Optional: restrict to one subject, e.g. 'Mathematics'",
                }
            },
        },
    },
    {
        "name": "find_standard",
        "description": (
            "Resolve a standard code (e.g. '4.OA.A.3', 'HS-LS2-5') to its official "
            "statement. The same code is reused across jurisdictions, so this usually "
            "returns several matches; 'Multi-State' is the Common Core / NGSS spine and "
            "sorts first. Filter by jurisdiction or subject to narrow."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "statementCode": {"type": "string"},
                "jurisdiction": {"type": "string"},
                "subject": {"type": "string"},
                "limit": {"type": "integer", "default": 25},
            },
            "required": ["statementCode"],
        },
    },
    {
        "name": "search_standards",
        "description": (
            "Full-text search across every standard statement by topic or wording, for "
            "when you do not know the code. Ranked by BM25."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "jurisdiction": {"type": "string"},
                "subject": {"type": "string"},
                "gradeLevel": {"type": "string", "description": "Single grade, e.g. '4' or 'K'"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_learning_components",
        "description": (
            "Break a standard into the granular teachable skills that support it. "
            "Accepts an internal id, a caseIdentifierUUID, or a bare statement code."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"standard": {"type": "string"}},
            "required": ["standard"],
        },
    },
    {
        "name": "get_progression",
        "description": (
            "Prerequisite ('backward') or subsequent ('forward') standards. Progression "
            "edges are authored only on the Multi-State Mathematics spine, so for a state "
            "standard this bridges through the aligned Multi-State standard and maps "
            "results back to the original jurisdiction. Most ELA, Science, and Social "
            "Studies standards have no progression."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "standard": {"type": "string"},
                "direction": {
                    "type": "string",
                    "enum": ["backward", "forward"],
                    "default": "backward",
                },
                "limit": {"type": "integer", "default": 25},
            },
            "required": ["standard"],
        },
    },
    {
        "name": "crosswalk_standard",
        "description": (
            "Find equivalent standards in other jurisdictions. Alignment is hub-and-spoke "
            "through the Multi-State spine, so a state-to-state crosswalk is resolved with "
            "an automatic two-hop. Omit toJurisdiction to see every alignment."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "standard": {"type": "string"},
                "toJurisdiction": {"type": "string"},
                "limit": {"type": "integer", "default": 60},
            },
            "required": ["standard"],
        },
    },
    {
        "name": "get_standard_context",
        "description": (
            "Where a standard sits in its framework: the ancestor chain up to the "
            "framework root (domain, grade, strand) plus its direct children."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "standard": {"type": "string"},
                "maxDepth": {"type": "integer", "default": 6},
                "childLimit": {"type": "integer", "default": 40},
            },
            "required": ["standard"],
        },
    },
    {
        "name": "find_curriculum",
        "description": (
            "Lessons, activities, and assessments aligned to a standard. All curriculum "
            "in the graph aligns to Multi-State Mathematics, so for a state standard this "
            "bridges automatically. Non-math standards have none."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "standard": {"type": "string"},
                "kind": {
                    "type": "string",
                    "enum": ["Lesson", "Activity", "Assessment", "LessonGrouping", "Course"],
                },
                "limit": {"type": "integer", "default": 40},
            },
            "required": ["standard"],
        },
    },
    {
        "name": "get_node",
        "description": "Complete raw property bag for any node, by id or caseIdentifierUUID.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
]


def _handlers(g: Graph):
    return {
        "graph_stats": lambda: g.stats(),
        "verify_alignment_claim": lambda statementCode, jurisdiction, subject=None: (
            g.verify_alignment_claim(statementCode, jurisdiction, subject)
        ),
        "coverage_report": lambda subject=None: g.coverage_report(subject),
        "find_standard": lambda statementCode, jurisdiction=None, subject=None, limit=25: (
            g.find_standard(statementCode, jurisdiction, subject, limit)
        ),
        "search_standards": lambda query, jurisdiction=None, subject=None, gradeLevel=None,
        limit=20: g.search_standards(query, jurisdiction, subject, gradeLevel, limit),
        "get_learning_components": lambda standard: g.learning_components(standard),
        "get_progression": lambda standard, direction="backward", limit=25: g.progression(
            standard, direction, limit
        ),
        "crosswalk_standard": lambda standard, toJurisdiction=None, limit=60: g.crosswalk(
            standard, toJurisdiction, limit
        ),
        "get_standard_context": lambda standard, maxDepth=6, childLimit=40: g.context(
            standard, maxDepth, childLimit
        ),
        "find_curriculum": lambda standard, kind=None, limit=40: g.curriculum(
            standard, kind, limit
        ),
        "get_node": lambda id: g.node(id),
    }


def _prune(o):
    if isinstance(o, dict):
        return {k: _prune(v) for k, v in o.items() if v is not None}
    if isinstance(o, list):
        return [_prune(v) for v in o]
    return o


def _send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _handle(req, handlers):
    method, rid = req.get("method"), req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": INSTRUCTIONS,
            },
        }
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}

    if method == "tools/call":
        params = req.get("params") or {}
        fn = handlers.get(params.get("name"))
        if not fn:
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32601, "message": f"unknown tool: {params.get('name')}"},
            }
        try:
            result = _prune(fn(**(params.get("arguments") or {})))
            payload = {"content": [{"type": "text", "text": json.dumps(result, indent=1)}]}
        except (GraphError, TypeError, ValueError) as e:
            payload = {
                "content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}],
                "isError": True,
            }
        return {"jsonrpc": "2.0", "id": rid, "result": payload}

    if rid is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": rid,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


def serve(db_path=None):
    db_path = db_path or os.environ.get("COLLECTIVE_DB")
    if not db_path:
        raise GraphError("no mirror path — pass one or set COLLECTIVE_DB")
    g = Graph(db_path)
    handlers = _handlers(g)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            continue
        try:
            resp = _handle(req, handlers)
        except Exception as e:  # noqa: BLE001 — one bad request must never kill the server
            resp = {
                "jsonrpc": "2.0",
                "id": req.get("id"),
                "error": {"code": -32603, "message": str(e)},
            }
        if resp is not None:
            _send(resp)


if __name__ == "__main__":
    serve(sys.argv[1] if len(sys.argv) > 1 else None)
