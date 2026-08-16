"""Shared fixture: a tiny synthetic mirror, not the 700MB national graph.

It reproduces the three topology facts that actually break queries: a code
reused across jurisdictions, progression edges only on the Multi-State spine,
and hub-and-spoke alignment. If a refactor drops the bridging, tests fail —
which is the point.
"""

import json
import sqlite3

import pytest

from learningnet.build import FTS, INDEXES, SCHEMA
from learningnet.graph import Graph


def _node(i, label, **p):
    return (
        i, label, p.get("name"), p.get("statementCode"), p.get("caseIdentifierUUID"),
        p.get("jurisdiction"), p.get("academicSubject"), p.get("gradeLevel"),
        p.get("statementType"), p.get("description"), json.dumps(p),
    )


@pytest.fixture
def mirror(tmp_path):
    db = tmp_path / "kg.sqlite"
    con = sqlite3.connect(db)
    con.executescript(SCHEMA)
    nodes = [
        _node("ms-1", "StandardsFrameworkItem", statementCode="4.OA.A.3",
              jurisdiction="Multi-State", academicSubject="Mathematics",
              gradeLevel='["4"]', description="Solve multistep word problems."),
        _node("ca-1", "StandardsFrameworkItem", statementCode="4.OA.A.3",
              jurisdiction="California", academicSubject="Mathematics",
              gradeLevel='["4"]', description="Solve multistep word problems."),
        _node("tx-1", "StandardsFrameworkItem", statementCode="111.6.b.5.A",
              jurisdiction="Texas", academicSubject="Mathematics",
              gradeLevel='["4"]', description="Represent multi-step problems."),
        _node("ms-0", "StandardsFrameworkItem", statementCode="3.OA.A.1",
              jurisdiction="Multi-State", academicSubject="Mathematics",
              gradeLevel='["3"]', description="Interpret products of whole numbers."),
        _node("lc-1", "LearningComponent", academicSubject="Mathematics",
              description="Solve multi-step real-world problems."),
        _node("les-1", "Lesson", name="Multi-Step Measurement Problems",
              academicSubject="Mathematics", gradeLevel='["4"]'),
    ]
    con.executemany("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?,?)", nodes)
    con.executemany("INSERT INTO edges VALUES(?,?,?,?,?,?)", [
        # alignment is hub-and-spoke: states link to the spine, never to each other
        ("e1", "hasStandardAlignment", "ca-1", "ms-1", "StandardsFrameworkItem",
         "StandardsFrameworkItem"),
        ("e2", "hasStandardAlignment", "tx-1", "ms-1", "StandardsFrameworkItem",
         "StandardsFrameworkItem"),
        # progression lives only on the spine
        ("e3", "buildsTowards", "ms-0", "ms-1", "StandardsFrameworkItem",
         "StandardsFrameworkItem"),
        # curriculum aligns only to the spine
        ("e4", "hasEducationalAlignment", "les-1", "ms-1", "Lesson",
         "StandardsFrameworkItem"),
        ("e5", "supports", "lc-1", "ca-1", "LearningComponent", "StandardsFrameworkItem"),
    ])
    for s in INDEXES:
        con.execute(s)
    con.executescript(FTS)
    con.executemany("INSERT INTO meta VALUES(?,?)",
                    [("builtAt", "2026-08-15T00:00:00Z"), ("source", "test")])
    con.commit()
    con.close()
    g = Graph(db)
    yield g
    g.close()
