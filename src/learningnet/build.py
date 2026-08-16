"""Build a Learning Net mirror from a Learning Commons export.

Reads `nodes.jsonl` and `relationships.jsonl` and produces an indexed SQLite
database with full-text search. Stdlib only — a school IT admin with a stock
Python install can run this.

Roughly 40 seconds and ~700 MB for the full national graph.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time

BATCH = 20_000

SCHEMA = """
DROP TABLE IF EXISTS nodes;
CREATE TABLE nodes(
  id             TEXT PRIMARY KEY,
  label          TEXT,
  name           TEXT,
  statement_code TEXT,
  case_uuid      TEXT,
  jurisdiction   TEXT,
  subject        TEXT,
  grade_level    TEXT,
  statement_type TEXT,
  description    TEXT,
  props          TEXT
);
DROP TABLE IF EXISTS edges;
CREATE TABLE edges(
  id        TEXT,
  label     TEXT,
  src       TEXT,
  dst       TEXT,
  src_label TEXT,
  dst_label TEXT
);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
"""

INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_e_src   ON edges(src, label)",
    "CREATE INDEX IF NOT EXISTS ix_e_dst   ON edges(dst, label)",
    "CREATE INDEX IF NOT EXISTS ix_e_lab   ON edges(label)",
    "CREATE INDEX IF NOT EXISTS ix_n_code  ON nodes(statement_code)",
    "CREATE INDEX IF NOT EXISTS ix_n_case  ON nodes(case_uuid)",
    "CREATE INDEX IF NOT EXISTS ix_n_label ON nodes(label)",
    "CREATE INDEX IF NOT EXISTS ix_n_juris ON nodes(jurisdiction, subject)",
)

FTS = """
DROP TABLE IF EXISTS nodes_fts;
CREATE VIRTUAL TABLE nodes_fts USING fts5(
  id UNINDEXED, statement_code, name, description,
  tokenize='porter unicode61');
INSERT INTO nodes_fts
  SELECT id, COALESCE(statement_code,''), COALESCE(name,''), COALESCE(description,'')
  FROM nodes;
"""

NODE_INSERT = "INSERT OR REPLACE INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?,?)"
EDGE_INSERT = "INSERT INTO edges VALUES(?,?,?,?,?,?)"


def _digest(path, chunk=1 << 20):
    """Content hash of a source file, so a rebuild can prove what it came from."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def _node_row(d):
    p = d.get("properties") or {}
    gl = p.get("gradeLevel")
    if isinstance(gl, list):
        gl = json.dumps(gl)
    return (
        d["identifier"],
        (d.get("labels") or [""])[0],
        p.get("name"),
        p.get("statementCode"),
        p.get("caseIdentifierUUID"),
        p.get("jurisdiction"),
        p.get("academicSubject"),
        gl,
        p.get("normalizedStatementType") or p.get("statementType"),
        p.get("description"),
        json.dumps(p, separators=(",", ":")),
    )


def _edge_row(d):
    return (
        d.get("identifier"),
        d.get("label"),
        d.get("source_identifier"),
        d.get("target_identifier"),
        (d.get("source_labels") or [""])[0],
        (d.get("target_labels") or [""])[0],
    )


def _ingest(con, path, sql, to_row):
    n, batch = 0, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            batch.append(to_row(json.loads(line)))
            n += 1
            if len(batch) >= BATCH:
                con.executemany(sql, batch)
                batch = []
    if batch:
        con.executemany(sql, batch)
    con.commit()
    return n


def build(export_dir, db_path, source="local-export", kg_version=None, log=print):
    """Build the mirror. Returns a provenance dict, also stored in `meta`."""
    nodes_f = os.path.join(export_dir, "nodes.jsonl")
    rels_f = os.path.join(export_dir, "relationships.jsonl")
    for f in (nodes_f, rels_f):
        if not os.path.exists(f):
            raise FileNotFoundError(f)

    os.makedirs(os.path.dirname(os.path.abspath(db_path)) or ".", exist_ok=True)

    # Build into a scratch file and rename into place at the end.
    #
    # The build runs with journal_mode=OFF and synchronous=OFF, which is what
    # makes it fast and also means an interrupted build leaves an unrecoverable
    # database. Doing that to the file someone is currently serving from is
    # unacceptable — and worse, the corrupt file then fails on the NEXT build
    # too, because executescript cannot even read it to drop the tables. So the
    # live mirror is never opened for writing: it is replaced, atomically, only
    # once a build has fully succeeded.
    tmp_path = db_path + ".building"
    for stale in (tmp_path, tmp_path + "-journal", tmp_path + "-wal"):
        if os.path.exists(stale):
            os.remove(stale)

    con = sqlite3.connect(tmp_path)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    con.executescript(SCHEMA)

    t = time.time()
    n = _ingest(con, nodes_f, NODE_INSERT, _node_row)
    log(f"  nodes      {n:>9,}  ({time.time() - t:.1f}s)")

    t = time.time()
    m = _ingest(con, rels_f, EDGE_INSERT, _edge_row)
    log(f"  edges      {m:>9,}  ({time.time() - t:.1f}s)")

    t = time.time()
    for s in INDEXES:
        con.execute(s)
    con.commit()
    log(f"  indexes               ({time.time() - t:.1f}s)")

    t = time.time()
    con.executescript(FTS)
    con.commit()
    log(f"  full-text             ({time.time() - t:.1f}s)")

    prov = {
        "builtAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": source,
        # The upstream release this mirror is a copy of. Learning Commons puts
        # the version in the CDN path, which is what makes this knowable at all
        # — without it a mirror can only report its own build time.
        "kgVersion": kg_version or "unknown",
        "nodeCount": str(n),
        "edgeCount": str(m),
        "nodesSha256": _digest(nodes_f),
        "relationshipsSha256": _digest(rels_f),
        "builderVersion": "0.1.0",
    }
    con.executemany("INSERT OR REPLACE INTO meta VALUES(?,?)", list(prov.items()))
    con.commit()
    con.close()

    # Only now does the live mirror change. os.replace is atomic on POSIX and
    # Windows, so a reader either sees the whole old mirror or the whole new one.
    os.replace(tmp_path, db_path)

    size = os.path.getsize(db_path) / 1e9
    log(f"\n  {db_path}  ({size:.2f} GB)")
    return prov
